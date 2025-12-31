# src/printtune/core/policy.py
from __future__ import annotations

from .log_types import SessionRecord

MAX_REJUDGE = 2
# rejudge回数上限を計算する関数

def count_rejudge(session: SessionRecord) -> int:
    return sum(1 for r in session.rounds if r.purpose == "rejudge")

def can_rejudge(session: SessionRecord) -> bool:
    return count_rejudge(session) < MAX_REJUDGE
