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

"""
OA L4の割り当て方針
f1 → 露出（exposure_stops）：一番大きく振る

f2 → コントラスト＋ガンマ：階調の硬さと暗部潰れのバランス

f3 → 色温度（temp）：寒色/暖色の方向性のみをテスト

saturation は Round1では固定 1.0（色の“量”は後回し）

この方針であれば、ユーザーは「暗い/明るい」「締まり/眠い」「寒色/暖色」をそれぞれ比較しやすく、PairwiseGPも“どの軸方向が好まれたか”を混同せずに初期ポスターIORを得られます。
"""

def factors_to_globals(f: dict[str, float]) -> dict:
    f1, f2, f3 = float(f["f1"]), float(f["f2"]), float(f["f3"])

    return {
        # f1: 露出。一番大きく振る。
        "exposure_stops": 0.8 * f1,

        # f2: コントラスト＋ガンマ連動。
        "contrast": 1.0 + 0.20 * f2,
        "gamma": 1.0 - 0.15 * f2,

        # f3: ホワイトバランス（色温度のみ）。
        "temp": 0.5 * f3,
        "tint": 0.0,

        # 彩度は初期は固定。
        "saturation": 1.0,
    }
