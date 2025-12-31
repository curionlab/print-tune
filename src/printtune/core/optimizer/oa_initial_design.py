# src/printtune/core/optimizer/oa_initial_design.py
from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class OACandidateSpec:
    slot: str
    factors: dict[str, float]  # -1..+1（後で実スケールへ）

# L4(2^3)相当の符号パターン（最小の直交配置）
L4 = [
    OACandidateSpec("A", {"f1": -1.0, "f2": -1.0, "f3": -1.0}),
    OACandidateSpec("B", {"f1": -1.0, "f2": +1.0, "f3": +1.0}),
    OACandidateSpec("C", {"f1": +1.0, "f2": -1.0, "f3": +1.0}),
    OACandidateSpec("D", {"f1": +1.0, "f2": +1.0, "f3": -1.0}),
]
