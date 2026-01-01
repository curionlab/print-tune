# src/printtune/core/log_types.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional
from datetime import datetime, timezone

JudgmentKind = Literal["chosen", "undecidable", "both_bad"]
RoundMode = Literal["oa", "pairwise"]
RoundPurpose = Literal["initial_oa", "pairwise_explore", "rejudge", "reprint"]

@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    slot: str
    params: dict

@dataclass(frozen=True)
class RoundRecord:
    round_id: str
    round_index: int
    created_at: str
    candidates: list[Candidate]

    mode: RoundMode = "pairwise"
    purpose: RoundPurpose = "pairwise_explore"
    rubric: Optional[str] = None
    delta_scale: float = 1.0

    judgment: Optional[dict] = None
    # judgment例:
    # {"kind":"chosen","chosen_slot":"A","at":...}
    # {"kind":"undecidable","at":...,"rubric":"skin","next_action":"rejudge"}
    # {"kind":"both_bad","at":...,"rubric":"overall","next_action":"reprint"}

    meta: dict = field(default_factory=dict)

@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    created_at: str
    sample_image_relpath: str

    rounds: list[RoundRecord] = field(default_factory=list)
    comparisons_global: list[list[int]] = field(default_factory=list)

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


