# src/printtune/core/botorch/propose_next.py
from __future__ import annotations

from dataclasses import dataclass
import torch
from botorch.optim import optimize_acqf
from botorch.acquisition.preference import AnalyticExpectedUtilityOfBestOption
from .bounds_builder import build_bounds

@dataclass(frozen=True)
class ProposedBatch:
    X_next: torch.Tensor  # (q, d)

def propose_next_pair(
    model,
    center: torch.Tensor,
    active_mask: torch.Tensor,
    delta: float,
    micro_ratio: float = 0.15,
    q: int = 2,
    num_restarts: int = 10,
    raw_samples: int = 128,
) -> ProposedBatch:
    acqf = AnalyticExpectedUtilityOfBestOption(pref_model=model)  # [web:235]
    bounds = build_bounds(center=center, active_mask=active_mask, delta=delta, micro_ratio=micro_ratio)

    X_next, _ = optimize_acqf(
        acq_function=acqf,
        bounds=bounds,
        q=q,
        num_restarts=num_restarts,
        raw_samples=raw_samples,
    )
    return ProposedBatch(X_next=X_next)