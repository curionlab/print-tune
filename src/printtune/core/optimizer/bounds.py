# src/printtune/core/optimizer/bounds.py
from __future__ import annotations
import torch

def default_bounds(d: int) -> torch.Tensor:
    lo = torch.full((d,), -1.0)
    hi = torch.full((d,), +1.0)
    return torch.stack([lo, hi], dim=0)
