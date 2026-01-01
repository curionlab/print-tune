# src/printtune/core/usecases.py
from __future__ import annotations

from typing import Optional, Literal

from .log_types import SessionRecord
from .session_runner import (
    apply_judgment_chosen,
    apply_judgment_undecidable,
    apply_judgment_both_bad,
)
from .session_loop import make_next_round
from .policy import can_rejudge


Kind = Literal["chosen", "undecidable", "both_bad"]
NextAction = Literal["rejudge", "reprint"]

# アプリ全体で共有すべき定数（本来は config.py や policy.py に置くべきですが、ここに定義またはimport）
MAX_ROUNDS = 10 

def submit_judgment_and_maybe_create_next_round(
    session: SessionRecord,
    round_index: int,
    kind: Kind,
    chosen_slot: Optional[str] = None,
    rubric: Optional[str] = None,
    next_action: Optional[NextAction] = None,
    delta_scale: float = 1.0,
) -> SessionRecord:
    """
    判定をSessionに反映し、必要なら次Roundを生成する。

    Args:
        session: セッション。
        round_index: 判定対象のround_index（1始まり）。
        kind: chosen / undecidable / both_bad。
        chosen_slot: kindがchosen、またはundecidable+rejudgeのとき必須。
        rubric: undecidable/both_badのとき必須。
        next_action: undecidableのとき必須（rejudge/reprint）。
        delta_scale: reprint時の探索幅係数。

    Returns:
        更新後のsession。
        
    Note:
        - chosen: 次のラウンド（pairwise_explore）を作成
        - undecidable+rejudge: 「迷ったけど、rubric観点から選ぶ」
          → undecidable判定を残しつつ、chosen扱いで比較データを増やす
          → 次はpairwise_exploreへ進む（rubricは次Roundのactive_keys重み付けに使う）
        - undecidable+reprint: 探索幅を広げて候補を再生成
        - both_bad: 必ずreprint
    """
    
    # 1. 判定の適用 (Judgment)
    if kind == "chosen":
        if chosen_slot is None:
            raise ValueError("chosen_slot required")
        session = apply_judgment_chosen(session, round_index=round_index, chosen_slot=chosen_slot)
        
        # Chosenの場合は、次は通常の pairwise_explore
        intent = "pairwise_explore"
        
    elif kind == "undecidable":
        if rubric is None or next_action is None:
            raise ValueError("rubric and next_action required")

        session = apply_judgment_undecidable(
            session, round_index=round_index, rubric=rubric, next_action=next_action
        ) # type: ignore

        if next_action == "rejudge":
            if chosen_slot is None:
                raise ValueError("chosen_slot required for undecidable+rejudge")

            # rejudge上限チェック -> 超過ならreprintへ
            if not can_rejudge(session):
                intent = "reprint"
            else:
                # 比較データ追加 (chosen適用)
                session = apply_judgment_chosen(session, round_index=round_index, chosen_slot=chosen_slot)
                intent = "pairwise_explore"
        else:
            # reprint
            intent = "reprint"
            
    elif kind == "both_bad":
        if rubric is None:
            raise ValueError("rubric required")
        
        session = apply_judgment_both_bad(session, round_index=round_index, rubric=rubric) # type: ignore
        intent = "reprint"
        
    else:
        raise ValueError(f"unknown kind: {kind}")


    # 2. 次ラウンド生成 (Next Round Creation)
    # 既に最大ラウンドに達している場合は生成しない
    if len(session.rounds) >= MAX_ROUNDS:
        return session

    return make_next_round(
        session, 
        intent=intent, # type: ignore
        rubric=rubric, 
        delta_scale=delta_scale
    )