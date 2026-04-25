# src/printtune/core/session_runner.py
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from PIL import Image
from typing import Literal

from .ids import SessionId, RoundId, CandidateId
from .log_types import SessionRecord, RoundRecord, Candidate, now_iso
from .optimizer.oa_initial_design import L4, factors_to_globals
from .optimizer.candidate_factory import make_candidates_from_X
from .imaging.sheet_layout import SheetCell, render_sheet_2x2
from .imaging.params_adapter import candidate_to_global_params
from .imaging.pipeline import render_image_with_global_params
from .imaging.transform import apply_simple_transform
from .imaging.frame import compose_with_evaluation_frame
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

# src/printtune/core/session_runner.py

def create_round1(session: SessionRecord) -> RoundRecord:
    # default_globals_v1 を import
    from .optimizer.param_space_v1 import PARAM_KEYS_V1, default_globals_v1
    
    rid = RoundId.new(SessionId(session.session_id), round_index=1)
    
    # 診断用: 差分定義 (中心 0.0)
    # A: Baseline, B: Temp+3.0, C: Tint+5.0, D: Exposure-0.25
    diagnostic_diffs = [
        [0.0] * len(PARAM_KEYS_V1), # A
        [3.0 if k == "temp" else 0.0 for k in PARAM_KEYS_V1], # B
        [5.0 if k == "tint" else 0.0 for k in PARAM_KEYS_V1], # C
        [-0.25 if k == "exposure_stops" else 0.0 for k in PARAM_KEYS_V1], # D
    ]
        
    candidates: list[Candidate] = []
    slots = ["A", "B", "C", "D"]
    
    for slot, diff_vec in zip(slots, diagnostic_diffs):
        cid = CandidateId.new(rid, slot=slot)
        
        # 【修正】ここで「デフォルト値 + 差分」を計算して絶対値(globals)にする
        g = default_globals_v1()
        for k, diff in zip(PARAM_KEYS_V1, diff_vec):
            g[k] += diff
        
        candidates.append(Candidate(
            candidate_id=cid.value,
            slot=slot,
            params={"globals": g},
        ))

    from .policy_axes import schedule_for_round
    sched = schedule_for_round(1)
    
    return RoundRecord(
        round_id=rid.value,
        round_index=1,
        created_at=now_iso(),
        candidates=candidates,
        mode="oa",
        purpose="initial_oa",
        delta_scale=1.0, # 初期値
        meta={"schedule": {
             "active_keys": list(sched.active_keys),
             "delta": sched.delta,
             "micro_ratio": sched.micro_ratio
        }}
    )

def render_round_sheet(sample_img: Image.Image, round_rec: RoundRecord, out_dir: Path, use_evaluation_frame: bool = True) -> Path:
    """
    Args:
        sample_img: 元の写真
        round_rec: ラウンドレコード
        out_dir: 出力ディレクトリ
        use_evaluation_frame: 評価用フレームを適用するか（デフォルト: True）
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    blank = Image.new("RGB", sample_img.size, (255, 255, 255))
    cells: list[SheetCell] = []

    for c in round_rec.candidates:
        gp = candidate_to_global_params(c)
        img_k = render_image_with_global_params(sample_img, gp)
        # 評価用フレームを適用
        if use_evaluation_frame:
            img_k = compose_with_evaluation_frame(img_k)
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