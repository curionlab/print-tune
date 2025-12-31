# src/printtune/core/usecases.py
from __future__ import annotations

from dataclasses import replace
from typing import Optional

from .log_types import SessionRecord
from .session_runner import apply_judgment_chosen, apply_judgment_undecidable, apply_judgment_both_bad
from .session_loop import make_next_round
from .policy import can_rejudge

def submit_judgment_and_maybe_create_next_round(
    session: SessionRecord,
    round_index: int,
    kind: str,
    chosen_slot: Optional[str] = None,
    rubric: Optional[str] = None,
    next_action: Optional[str] = None,
    delta_scale: float = 1.0,
) -> SessionRecord:
    if kind == "chosen":
        if chosen_slot is None:
            raise ValueError("chosen_slot required")
        return apply_judgment_chosen(session, round_index=round_index, chosen_slot=chosen_slot)

    if kind == "undecidable":
        if rubric is None or next_action is None:
            raise ValueError("rubric and next_action required")
        session = apply_judgment_undecidable(session, round_index=round_index, rubric=rubric, next_action=next_action)  # type: ignore[arg-type]
        if next_action == "rejudge" and not can_rejudge(session):
            # 上限超過ならreprintへフォールバック
            next_action = "reprint"
        return make_next_round(session, intent=next_action, rubric=rubric, delta_scale=delta_scale)  # type: ignore[arg-type]

    if kind == "both_bad":
        if rubric is None:
            raise ValueError("rubric required")
        session = apply_judgment_both_bad(session, round_index=round_index, rubric=rubric)  # type: ignore[arg-type]
        return make_next_round(session, intent="reprint", rubric=rubric, delta_scale=delta_scale)

    raise ValueError(f"unknown kind: {kind}")
