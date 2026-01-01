# src/printtune/core/policy_axes.py
from dataclasses import dataclass
from typing import Sequence

"""
設計方針
Round1（OA）：粗探索（全体の当たりを付ける）

Round2：露出＋コントラスト（輝度基盤を先に決める）

Round3：Temp＋Tint（色被りの補正）

Round4：Saturation＋Gamma（色量と暗部階調の整形）

Round5：微調整（上で良かった軸のΔを小さく）

「まずWB、その後露出/コントラスト、その後色」という順番は実務的なワークフローでもよく語られます。

"""
@dataclass(frozen=True)
class AxisSchedule:
    round_index: int
    active_keys: Sequence[str]
    delta: float  # 正規化空間での提案幅
    micro_ratio: float = 0.15

# Round5は全軸を再度開放（相互作用吸収）
SCHEDULE = [
    AxisSchedule(1, ["exposure_stops","contrast","gamma","temp","tint"], delta=0.60, micro_ratio=0.20),
    AxisSchedule(2, ["exposure_stops","contrast","gamma"], delta=0.35, micro_ratio=0.15),
    AxisSchedule(3, ["temp","tint"], delta=0.30, micro_ratio=0.15),
    AxisSchedule(4, ["saturation","gamma"], delta=0.25, micro_ratio=0.15),
    AxisSchedule(5, ["exposure_stops","contrast","gamma","temp","tint","saturation"], delta=0.15, micro_ratio=0.10),
]


def schedule_for_round(round_index: int) -> AxisSchedule:
    for s in SCHEDULE:
        if s.round_index == round_index:
            return s
    # 6回目以降はRound5相当（微調整）
    return AxisSchedule(round_index, SCHEDULE[-1].active_keys, delta=SCHEDULE[-1].delta)
