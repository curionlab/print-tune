# src/printtune/core/optimizer/candidate_factory.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..ids import CandidateId, RoundId
from ..log_types import Candidate
from .params_space import PARAM_KEYS

def x_to_params(x: list[float]) -> dict:
    return {"x": {k: float(v) for k, v in zip(PARAM_KEYS, x, strict=True)}}

def make_candidates_from_X(round_id: RoundId, slots: Iterable[str], X: list[list[float]]) -> list[Candidate]:
    cands: list[Candidate] = []
    for slot, x in zip(list(slots), X, strict=True):
        cid = CandidateId.new(round_id, slot=slot)
        cands.append(Candidate(candidate_id=cid.value, slot=slot, params=x_to_params(x)))
    return cands
