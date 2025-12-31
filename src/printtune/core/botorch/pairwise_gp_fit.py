# src/printtune/core/botorch/pairwise_gp_fit.py
from __future__ import annotations

import torch
from botorch.models import PairwiseGP
from botorch.fit import fit_gpytorch_mll
from botorch.models.transforms import Normalize
from botorch.models.pairwise_gp import PairwiseGP, PairwiseLaplaceMarginalLogLikelihood

def fit_pairwise_gp(train_X: torch.Tensor, train_comp: torch.LongTensor) -> PairwiseGP:
    # BoTorch requires double precision (float64) for numerical stability
    train_X = train_X.to(dtype=torch.float64)
    d = train_X.shape[-1]
    model = PairwiseGP(train_X, train_comp, input_transform=Normalize(d=d))
    mll = PairwiseLaplaceMarginalLogLikelihood(model.likelihood, model)
    fit_gpytorch_mll(mll)
    return model
