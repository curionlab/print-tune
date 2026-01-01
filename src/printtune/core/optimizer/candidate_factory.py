# src/printtune/core/optimizer/candidate_factory.py
from __future__ import annotations

from typing import Iterable
from ..ids import CandidateId, RoundId
from ..log_types import Candidate
from .param_space_v1 import PARAM_KEYS_V1

def x_to_globals(x: list[float]) -> dict:
    return {k: float(v) for k, v in zip(PARAM_KEYS_V1, x, strict=True)}

def make_candidates_from_X(round_id: RoundId, slots: Iterable[str], X: list[list[float]]) -> list[Candidate]:
    cands: list[Candidate] = []
    for slot, x in zip(list(slots), X, strict=True):
        cid = CandidateId.new(round_id, slot=slot)
        cands.append(Candidate(
            candidate_id=cid.value,
            slot=slot,
            params={"globals": x_to_globals(x)},
        ))
    return cands
