# src/printtune/core/botorch/update_loop.py
from __future__ import annotations

from dataclasses import dataclass

import torch

from .build_data import build_torch_data
from .pairwise_gp_fit import fit_pairwise_gp
from .propose_next import propose_next_pair
from ..optimizer.bounds import default_bounds

@dataclass(frozen=True)
class NextProposal:
    X_next: list[list[float]]  # python listへ戻す（UI/ログで扱いやすく）

def propose_from_session(session) -> NextProposal:
    data = build_torch_data(session)
    model = fit_pairwise_gp(data.train_X, data.train_comp)
    bounds = default_bounds(d=data.train_X.shape[-1])
    proposed = propose_next_pair(model, bounds=bounds, q=2)
    X_next = proposed.X_next.detach().cpu().tolist()
    return NextProposal(X_next=X_next)
