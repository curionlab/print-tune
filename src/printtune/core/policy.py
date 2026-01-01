# src/printtune/core/policy.py
from __future__ import annotations

from .log_types import SessionRecord

MAX_REJUDGE = 2


def count_rejudge(session: SessionRecord) -> int:
    """
    undecidable判定のうち、rejudge actionを選んだ回数を数える。
    
    Note:
        rejudgeは「微妙な差を何度も判定せず、次に進む」ための制限。
        purpose="rejudge"のRoundではなく、judgment.next_action="rejudge"で数える。
    """
    count = 0
    for r in session.rounds:
        j = r.judgment
        if j and j.get("kind") == "undecidable" and j.get("next_action") == "rejudge":
            count += 1
    return count


def can_rejudge(session: SessionRecord) -> bool:
    return count_rejudge(session) < MAX_REJUDGE
