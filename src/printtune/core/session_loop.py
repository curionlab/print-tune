# src/printtune/core/session_loop.py
from __future__ import annotations

from dataclasses import replace
from typing import Literal, Optional
import random

from .log_types import SessionRecord, RoundRecord, now_iso
from .ids import RoundId, SessionId
from .optimizer.candidate_factory import make_candidates_from_X
from .botorch.update_loop import propose_from_session

Intent = Literal["pairwise_explore", "rejudge", "reprint"]

def _next_round_index(session: SessionRecord) -> int:
    return len(session.rounds) + 1

def _new_round_id(session: SessionRecord, round_index: int) -> RoundId:
    return RoundId.new(SessionId(session.session_id), round_index=round_index)

def append_round(session: SessionRecord, rr: RoundRecord) -> SessionRecord:
    return replace(session, rounds=list(session.rounds) + [rr])

def make_next_round(
    session: SessionRecord,
    intent: Intent,
    rubric: Optional[str] = None,
    delta_scale: float = 1.0,
) -> SessionRecord:
    round_index = _next_round_index(session)
    rid = _new_round_id(session, round_index)

    if intent == "pairwise_explore":
        proposal = propose_from_session(session)
        cands = make_candidates_from_X(rid, slots=["A", "B"], X=proposal.X_next)
        rr = RoundRecord(
            round_id=rid.value,
            round_index=round_index,
            created_at=now_iso(),
            candidates=cands,
            mode="pairwise",
            purpose="pairwise_explore",
            rubric=rubric,
            delta_scale=1.0,
        )
        return append_round(session, rr)

    prev = session.rounds[-1]
    # 直前ラウンドの候補Xを抽出
    prev_X: list[list[float]] = []
    for c in prev.candidates[:2]:
        if "oa_factors" in c.params:
            f = c.params["oa_factors"]
            prev_X.append([float(f["f1"]), float(f["f2"]), float(f["f3"])])
        else:
            x = c.params["x"]
            prev_X.append([float(x["f1"]), float(x["f2"]), float(x["f3"])])

    if intent == "rejudge":
        cands = make_candidates_from_X(rid, slots=["A", "B"], X=prev_X[:2])
        rr = RoundRecord(
            round_id=rid.value,
            round_index=round_index,
            created_at=now_iso(),
            candidates=cands,
            mode=prev.mode,
            purpose="rejudge",
            rubric=rubric,
            delta_scale=1.0,
        )
        return append_round(session, rr)

    # reprint: 探索幅を増やして少し動かす（後で“軸スケジュール＋制約”に置換）
    delta = 0.35 * float(delta_scale)
    base = prev_X[0]
    X2 = [
        [max(-1.0, min(1.0, base[i] + (delta if i == 0 else 0.0))) for i in range(3)],
        [max(-1.0, min(1.0, base[i] - (delta if i == 0 else 0.0))) for i in range(3)],
    ]
    cands = make_candidates_from_X(rid, slots=["A", "B"], X=X2)
    rr = RoundRecord(
        round_id=rid.value,
        round_index=round_index,
        created_at=now_iso(),
        candidates=cands,
        mode=prev.mode,
        purpose="reprint",
        rubric=rubric,
        delta_scale=float(delta_scale),
    )
    return append_round(session, rr)
