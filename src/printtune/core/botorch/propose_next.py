# src/printtune/core/botorch/propose_next.py
from __future__ import annotations

from dataclasses import dataclass
import torch
from botorch.optim import optimize_acqf
from botorch.acquisition.preference import AnalyticExpectedUtilityOfBestOption

@dataclass(frozen=True)
class ProposedBatch:
    X_next: torch.Tensor  # (q, d)

def propose_next_pair(
    model,
    bounds: torch.Tensor,
    q: int = 2,
    num_restarts: int = 10,
    raw_samples: int = 128,
) -> ProposedBatch:
    # EUBOは preference_bo tutorialで示される主要手法 [web:235]
    acqf = AnalyticExpectedUtilityOfBestOption(pref_model=model)

    X_next, _ = optimize_acqf(
        acq_function=acqf,
        bounds=bounds,
        q=q,
        num_restarts=num_restarts,
        raw_samples=raw_samples,
    )
    return ProposedBatch(X_next=X_next)
