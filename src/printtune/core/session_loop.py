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
    """
    次のラウンドを作成する主要なエントリーポイント。
    """
    # フェーズとしてのラウンド番号（スケジュール進行に使う）と
    # セッション内での通算ラウンド番号を取得
    phase_round_index = _phase_round_index_for_intent(session, intent)
    round_index = _next_round_index(session)
    rid = _new_round_id(session, round_index)

    # 1. pairwise_explore: BoTorch提案を使う（基本ルート）
    if intent == "pairwise_explore":
        from .botorch.update_loop import propose_from_session_for_round
        # rubric を考慮したスケジュールに基づいて次候補を提案
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
                "phase_round_index": phase_round_index
            },
        )
        return append_round(session, rr)

    # 直前ラウンド情報を取得（rejudge/reprint用）
    prev = session.rounds[-1]

    # 2. rejudge: 直前と同じXで再生成（IDだけ振り直し）
    if intent == "rejudge":
        prev_X = [_extract_x_from_candidate(c) for c in prev.candidates]
        slots = [c.slot for c in prev.candidates]
        
        cands = make_candidates_from_X(rid, slots=slots, X=prev_X)

        rr = RoundRecord(
            round_id=rid.value,
            round_index=round_index,
            created_at=now_iso(),
            candidates=cands,
            mode=prev.mode,
            purpose="rejudge",
            rubric=rubric,
            delta_scale=1.0,
            meta={
                "source_round": prev.round_index, 
                "phase_round_index": phase_round_index
            },
        )
        return append_round(session, rr)

    # 3. reprint: 探索幅を増やして再提示（確定仕様）
    if intent == "reprint":
        from .policy_axes import schedule_for_round
        # スケジュールから基準となるdeltaと、動かすべき軸(rubricに基づく)を取得
        sched = schedule_for_round(phase_round_index, rubric=rubric, intent="reprint")
        applied_delta = sched.delta * delta_scale

        # 直前のスロットA（基準点）をベースに、指定された軸だけを±動かす
        base_X = _extract_x_from_candidate(prev.candidates[0])
        
        def clamp(v: float) -> float:
            return max(-1.0, min(1.0, v))

        # 新しい候補の生成：active_keysに含まれる軸だけを ±applied_delta 動かす
        new_X = []
        # A' : baseline + applied_delta (指定軸のみ)
        new_X.append([
            clamp(val + (applied_delta if PARAM_KEYS_V1[i] in sched.active_keys else 0.0))
            for i, val in enumerate(base_X)
        ])
        # B' : baseline - applied_delta (指定軸のみ)
        new_X.append([
            clamp(val - (applied_delta if PARAM_KEYS_V1[i] in sched.active_keys else 0.0))
            for i, val in enumerate(base_X)
        ])

        # reprintは、診断をしやすくするため常に2枚比較（Pairwise）とする
        slots = ["A", "B"]
        cands = make_candidates_from_X(rid, slots=slots, X=new_X)

        rr = RoundRecord(
            round_id=rid.value,
            round_index=round_index,
            created_at=now_iso(),
            candidates=cands,
            mode="pairwise",
            purpose="reprint",
            rubric=rubric,
            delta_scale=float(delta_scale),
            meta={
                "source_round": prev.round_index,
                "phase_round_index": phase_round_index,
                "delta_applied": applied_delta,
                "schedule": {
                    "active_keys": list(sched.active_keys),
                    "delta": sched.delta,
                    "micro_ratio": sched.micro_ratio
                }
            },
        )
        return append_round(session, rr)

    raise ValueError(f"unknown intent: {intent}")