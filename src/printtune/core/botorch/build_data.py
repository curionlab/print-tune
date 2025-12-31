# src/printtune/core/botorch/build_data.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import torch

from ..log_types import SessionRecord
from ..optimizer.params_space import factors_to_x, PARAM_KEYS

@dataclass(frozen=True)
class TorchPreferenceData:
    train_X: torch.Tensor        # (n, d)
    train_comp: torch.LongTensor # (m, 2)
    candidate_ids: list[str]     # index -> candidate_id

def build_torch_data(session: SessionRecord) -> TorchPreferenceData:
    # 1) 候補を時系列にフラット化（将来: roundを跨いで増える想定）
    candidate_ids: list[str] = []
    X_list: list[list[float]] = []

    for rr in session.rounds:
        for c in rr.candidates:
            candidate_ids.append(c.candidate_id)
            if "oa_factors" in c.params:
                x = factors_to_x(c.params["oa_factors"]).x
            else:
                # Round2以降: params["x"] を使う
                x = [float(c.params["x"][k]) for k in PARAM_KEYS]
            X_list.append(x)

    # 2) comparisons
    comps = session.comparisons_global
    if len(candidate_ids) == 0 or len(comps) == 0:
        raise ValueError("Need at least 1 candidate and 1 comparison to fit PairwiseGP.")

    train_X = torch.tensor(X_list, dtype=torch.float64)
    train_comp = torch.tensor(comps, dtype=torch.long)

    return TorchPreferenceData(train_X=train_X, train_comp=train_comp, candidate_ids=candidate_ids)
