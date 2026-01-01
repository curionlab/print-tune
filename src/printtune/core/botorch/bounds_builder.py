# src/printtune/core/botorch/bounds_builder.py
from __future__ import annotations
import torch
"""
2) micro-delta（非アクティブ軸を完全固定しない）
方針
active軸: center±delta

非active軸: center±(delta * micro_ratio)

micro_ratio は 0.15 くらいから開始

これで、ヘルムホルツ・コールラウシュ的な“色が明るさに見える”相互作用を吸収しやすくします。
"""

def build_bounds(center: torch.Tensor, active_mask: torch.Tensor, delta: float, micro_ratio: float = 0.15) -> torch.Tensor:
    d = center.numel()
    delta_vec = torch.full((d,), float(delta), device=center.device, dtype=center.dtype)
    micro = float(delta) * float(micro_ratio)
    delta_vec = torch.where(active_mask, delta_vec, torch.full((d,), micro, device=center.device, dtype=center.dtype))
    lo = torch.clamp(center - delta_vec, -1.0, 1.0)
    hi = torch.clamp(center + delta_vec, -1.0, 1.0)
    return torch.stack([lo, hi], dim=0)
