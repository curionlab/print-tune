# src/printtune/core/optimizer/param_space_v1.py
from __future__ import annotations

from dataclasses import dataclass

# まずは6軸（5〜8の範囲内）
# temp/tintは本来RAWやXYZ/LMSで扱うのが筋ですが、フェーズ1では「人間が操作できる軸」を
# 優先し、内部では線形RGB上の近似（チャネルゲイン＋回転）として扱います
#（フェーズ2以降でモデル化を洗練）。
# 温度/ティントがWBの主要2軸である点自体は一般に共有されているので、UIの軸としては妥当です。
PARAM_KEYS_V1 = [
    "exposure_stops",   # [-? , +?]
    "contrast",         # [0.8, 1.2] 等（線形領域）
    "saturation",       # [0.8, 1.2] 等（線形領域での近似）
    "temp",             # 色温度軸（便宜的な正規化値）
    "tint",             # 緑-マゼンタ軸（正規化）
    "gamma",            # 追加：暗部持ち上げ/潰し回避
]

@dataclass(frozen=True)
class ParamVectorV1:
    values: dict[str, float]

    def to_x(self) -> list[float]:
        return [float(self.values[k]) for k in PARAM_KEYS_V1]
