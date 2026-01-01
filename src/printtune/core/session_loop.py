# src/printtune/core/session_loop.py
from __future__ import annotations

from dataclasses import replace
from typing import Literal, Optional

import random

from .log_types import SessionRecord, RoundRecord, now_iso
from .ids import RoundId, SessionId
from .optimizer.candidate_factory import make_candidates_from_X
from .optimizer.param_space_v1 import PARAM_KEYS_V1
from .botorch.update_loop import propose_from_session_for_round, propose_reprint_pair
from .policy_axes import RUBRIC_TO_PRIORITY_KEYS, schedule_for_round


Intent = Literal["pairwise_explore", "reprint"]

def _next_round_index(session: SessionRecord) -> int:
    return len(session.rounds) + 1

def _new_round_id(session: SessionRecord, round_index: int) -> RoundId:
    return RoundId.new(SessionId(session.session_id), round_index=round_index)

def append_round(session: SessionRecord, rr: RoundRecord) -> SessionRecord:
    return replace(session, rounds=list(session.rounds) + [rr])

def _extract_x_from_candidate(c) -> list[float]:
    # globals 前提でXを抽出
    g = c.params.get("globals")
    if g is None:
        # 移行期ガード（万一古いデータがあれば）
        raise ValueError("candidate params missing 'globals'")
    return [float(g[k]) for k in PARAM_KEYS_V1]

def _count_pairwise_explore(session: SessionRecord) -> int:
    return sum(1 for r in session.rounds if r.purpose == "pairwise_explore")

def _phase_round_index_for_intent(session: SessionRecord, intent: str) -> int:
    """
    SCHEDULE用の段階(round_index)を返す。
    - pairwise_explore: 初回はRound2相当、以降はexplore回数に応じて 2,3,4,5... と進む。
    - reprint: 段階を進めない（現在段階を維持）。
    """
    n_explore = _count_pairwise_explore(session)

    if intent == "pairwise_explore":
        # 初回exploreはRound2相当
        return n_explore + 2
    if intent == "reprint":
        # 現在段階を維持（OAなら1、explore済みなら2,3,...）
        return n_explore + 1

    raise ValueError(f"unknown intent: {intent}")

def make_next_round(
    session: SessionRecord,
    intent: Intent,
    rubric: Optional[str] = None,
    delta_scale: float = 1.0,
) -> SessionRecord:
    round_index = _next_round_index(session)
    rid = _new_round_id(session, round_index)

    # 1. pairwise_explore: BoTorch提案を使う（基本ルート）
    if intent == "pairwise_explore":
        phase_round_index = _phase_round_index_for_intent(session, intent="pairwise_explore")
        proposal = propose_from_session_for_round(session, phase_round_index, rubric=rubric)

        cands = make_candidates_from_X(
            round_id=rid,
            slots=["A", "B"],
            X=proposal.X_next
        )
        
        rr = RoundRecord(
            round_id=rid.value,
            round_index=round_index,
            created_at=now_iso(),
            candidates=cands,
            mode="pairwise",
            purpose="pairwise_explore",
            rubric=rubric,
            delta_scale=1.0,
            meta={
                "schedule": proposal.schedule,
                "phase_round_index": phase_round_index,
            },
        )
        return append_round(session, rr)

    # 2) reprint: BoTorchベースの「制約付き再提案」へ移行
    prev = session.rounds[-1]
    phase_round_index = _phase_round_index_for_intent(session, intent="reprint")

    if prev.mode == "oa":
        # OA reprint は「4択で方向性を絞る」ためのものなので、
        # 直交表(=4候補の相対差)を壊さずに "全体を同じ方向へ" 動かす。
        # both_bad 等で正解(center)が無い状態でも意味があるように、ランダムは使わない。

        # scheduleは rubric を反映したactive_keysに寄せる（優先キーの並び替え等）
        phase_round_index = _phase_round_index_for_intent(session, intent="reprint")
        sched = schedule_for_round(phase_round_index, rubric=rubric)

        # どの軸を動かすか:
        # - exposure_stops が active ならそれ（「全体がダメ」を救う最優先）
        # - なければ scheduleの先頭キー（rubric反映後の並び）を採用
        if "exposure_stops" in list(sched.active_keys):
            shift_key = "exposure_stops"
        else:
            shift_key = list(sched.active_keys)[0]

        # シフト方向は決定的に交互 (+, -, +, ...) にする（ランダム禁止）
        n_oa_reprint = sum(
            1
            for r in session.rounds
            if r.purpose == "reprint" and getattr(r, "mode", None) == "oa"
        )
        shift_sign = 1.0 if (n_oa_reprint % 2 == 0) else -1.0

        # 旧ノウハウ: OA reprint は delta=0.35 * delta_scale を使う
        shift_delta = 0.35 * float(delta_scale)

        key_to_index = {k: i for i, k in enumerate(PARAM_KEYS_V1)}
        idx = key_to_index.get(shift_key, 0)

        def clamp(v: float) -> float:
            return max(-2.0, min(2.0, v))

        X_next: list[list[float]] = []
        for c in prev.candidates:
            base = _extract_x_from_candidate(c)
            shifted = [
                clamp(base[i] + (shift_sign * shift_delta if i == idx else 0.0))
                for i in range(len(base))
            ]
            X_next.append(shifted)

        slots = [c.slot for c in prev.candidates]
        schedule_meta = {
            "active_keys": list(sched.active_keys),
            "delta": float(sched.delta),
            "micro_ratio": float(sched.micro_ratio),
            "center_source": "oa_global_shift",
            "rubric": rubric,
            "shift_key": shift_key,
            "shift_sign": shift_sign,
            "shift_delta": shift_delta,
        }
    else:
        # pairwiseは2候補
        seed = random.randint(0, 2**31 - 1)
        p = propose_reprint_pair(
            session=session,
            phase_round_index=phase_round_index,
            rubric=rubric,
            delta_scale=float(delta_scale),
            q=2,
            seed=seed,
        )
        X_next = p.X_next
        slots = ["A", "B"]
        schedule_meta = dict(p.schedule)
        schedule_meta["seeds"] = [seed]
        schedule_meta["q_total"] = 2

    cands = make_candidates_from_X(
        round_id=rid,
        slots=slots,
        X=X_next,
    )

    rr = RoundRecord(
        round_id=rid.value,
        round_index=round_index,
        created_at=now_iso(),
        candidates=cands,
        mode=prev.mode,
        purpose="reprint",
        rubric=rubric,
        delta_scale=float(delta_scale),
        meta={
            "source_round": prev.round_index,
            "phase_round_index": phase_round_index,
            "schedule": schedule_meta,
        },
    )
    return append_round(session, rr)