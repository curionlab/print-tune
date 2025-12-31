# src/printtune/core/optimizer/params_space.py
from __future__ import annotations

from dataclasses import dataclass

# まずはOAの3因子だけを「連続ベクトル(3次元)」として扱う
# 将来: ここを3D LUT係数や軸スケジュールへ拡張しても、BoTorch側の入出力次元が崩れないようにする。
PARAM_KEYS = ["f1", "f2", "f3"]

@dataclass(frozen=True)
class CandidateParamVector:
    x: list[float]  # len=3

def factors_to_x(oa_factors: dict[str, float]) -> CandidateParamVector:
    return CandidateParamVector([float(oa_factors[k]) for k in PARAM_KEYS])
