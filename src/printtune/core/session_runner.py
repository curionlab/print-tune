# src/printtune/core/session_runner.py
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from PIL import Image
from typing import Literal

from .ids import SessionId, RoundId, CandidateId
from .log_types import SessionRecord, RoundRecord, Candidate, now_iso
from .optimizer.oa_initial_design import L4
from .optimizer.candidate_factory import make_candidates_from_X
from .imaging.sheet_layout import SheetCell, render_sheet_2x2
from .imaging.params_adapter import candidate_to_simple_params
from .imaging.transform import apply_simple_transform
from .io.paths import artifacts_dir
from .botorch.dataset import build_comparisons_from_choice

Rebric = Literal["overall", "skin", "neutral_gray", "saturation", "shadows", "highlights"]
NextAction = Literal["rejudge", "reprint"]

def new_session(sample_image_relpath: str) -> SessionRecord:
    sid = SessionId.new()
    return SessionRecord(
        session_id=sid.value,
        created_at=now_iso(),
        sample_image_relpath=sample_image_relpath,
        rounds=[],
        comparisons_global=[],
    )

def create_round1(session: SessionRecord) -> RoundRecord:
    rid = RoundId.new(SessionId(session.session_id), round_index=1)
    candidates: list[Candidate] = []
    for spec in L4:
        cid = CandidateId.new(rid, slot=spec.slot)
        candidates.append(Candidate(candidate_id=cid.value, slot=spec.slot, params={"oa_factors": spec.factors}))
    return RoundRecord(
        round_id=rid.value,
        round_index=1,
        created_at=now_iso(),
        candidates=candidates,
        mode="oa",
        purpose="initial_oa",
        delta_scale=1.0,
    )


def render_round_sheet(sample_img: Image.Image, round_rec: RoundRecord, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)

    blank = Image.new("RGB", sample_img.size, (255, 255, 255))
    cells: list[SheetCell] = []

    for c in round_rec.candidates:
        p = candidate_to_simple_params(c)
        img_k = apply_simple_transform(sample_img, p)
        cells.append(SheetCell(slot=c.slot, candidate_id=c.candidate_id, image=img_k))

    while len(cells) < 4:
        cells.append(SheetCell(slot="-", candidate_id="blank", image=blank))

    if len(cells) != 4:
        raise ValueError("round sheet currently supports up to 4 candidates.")

    cell_w = max(400, sample_img.width // 2)
    cell_h = max(400, sample_img.height // 2)

    sheet = render_sheet_2x2(cells, cell_w=cell_w, cell_h=cell_h, margin=20)
    out_path = out_dir / f"round{round_rec.round_index:02d}_sheet.png"
    sheet.save(out_path, format="PNG")
    return out_path

def _global_offset_for_round(session: SessionRecord, round_index: int) -> int:
    # round_indexは1始まり
    offset = 0
    for rr in session.rounds[: round_index - 1]:
        offset += len(rr.candidates)
    return offset

def apply_judgment_chosen(session: SessionRecord, round_index: int, chosen_slot: str) -> SessionRecord:
    rounds = list(session.rounds)
    rr = rounds[round_index - 1]
    slots = [c.slot for c in rr.candidates]
    if chosen_slot not in slots:
        raise ValueError(f"unknown slot: {chosen_slot}")

    winner_local = slots.index(chosen_slot)
    comps_local = build_comparisons_from_choice(winner_local, n_items=len(rr.candidates))

    offset = _global_offset_for_round(session, round_index=round_index)
    comps_global = [[a + offset, b + offset] for a, b in comps_local]

    rr2 = replace(rr, judgment={"kind": "chosen", "chosen_slot": chosen_slot, "at": now_iso()})
    rounds[round_index - 1] = rr2

    comps2 = list(session.comparisons_global) + comps_global
    return replace(session, rounds=rounds, comparisons_global=comps2)


def apply_judgment_undecidable(
    session: SessionRecord,
    round_index: int,
    rubric: Rubric,
    next_action: NextAction,
) -> SessionRecord:
    rounds = list(session.rounds)
    rr = rounds[round_index - 1]
    rr2 = replace(rr, judgment={
        "kind": "undecidable",
        "at": now_iso(),
        "rubric": rubric,
        "next_action": next_action,
    })
    rounds[round_index - 1] = rr2
    # comparisons_globalは増やさない
    return replace(session, rounds=rounds)


def apply_judgment_both_bad(
    session: SessionRecord,
    round_index: int,
    rubric: Rubric,
    next_action: Literal["reprint"] = "reprint",
) -> SessionRecord:
    rounds = list(session.rounds)
    rr = rounds[round_index - 1]
    rr2 = replace(rr, judgment={
        "kind": "both_bad",
        "at": now_iso(),
        "rubric": rubric,
        "next_action": next_action,
    })
    rounds[round_index - 1] = rr2
    return replace(session, rounds=rounds)


def artifacts_path_for_session(session_id: str) -> Path:
    return artifacts_dir(session_id)


def create_round2_from_proposal(session: SessionRecord, X_next: list[list[float]]) -> RoundRecord:
    rid = RoundId.new(SessionId(session.session_id), round_index=2)
    # 2点提案なので slotは仮にA/Bを使用（将来4点に戻してもslot体系は維持）
    candidates = make_candidates_from_X(rid, slots=["A", "B"], X=X_next)
    return RoundRecord(
        round_id=rid.value,
        round_index=2,
        created_at=now_iso(),
        candidates=candidates,
    )

def render_round2_sheet(sample_img: Image.Image, round_rec: RoundRecord, out_dir: Path) -> Path:
    # 2候補しかないので、4-upのうち下段を白にして「A/Bだけ」載せる（UI/運用が単純）
    out_dir.mkdir(parents=True, exist_ok=True)

    def cell_for(c: Candidate) -> SheetCell:
        return SheetCell(slot=c.slot, candidate_id=c.candidate_id, image=sample_img)

    blank = Image.new("RGB", sample_img.size, (255, 255, 255))
    cells = [
        cell_for(round_rec.candidates[0]),
        cell_for(round_rec.candidates[1]),
        SheetCell(slot="-", candidate_id="blank", image=blank),
        SheetCell(slot="-", candidate_id="blank", image=blank),
    ]

    cell_w = max(400, sample_img.width // 2)
    cell_h = max(400, sample_img.height // 2)
    sheet = render_sheet_2x2(cells, cell_w=cell_w, cell_h=cell_h, margin=20)
    out_path = out_dir / f"round{round_rec.round_index:02d}_sheet.png"
    sheet.save(out_path, format="PNG")
    return out_path

def append_round(session: SessionRecord, rr: RoundRecord) -> SessionRecord:
    rounds2 = list(session.rounds) + [rr]
    return replace(session, rounds=rounds2)