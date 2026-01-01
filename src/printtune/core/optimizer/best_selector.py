# src/printtune/core/optimizer/best_selector.py
from __future__ import annotations
from ..log_types import SessionRecord
from .center import extract_last_chosen_center
from .param_space_v1 import PARAM_KEYS_V1

def extract_last_chosen_globals(session: SessionRecord) -> dict:
    for rr in reversed(session.rounds):
        j = rr.judgment or {}
        if j.get("kind") == "chosen":
            slot = j["chosen_slot"]
            for c in rr.candidates:
                if c.slot == slot:
                    return dict(c.params["globals"])
    # fallback: last round first candidate
    return dict(session.rounds[-1].candidates[0].params["globals"])
