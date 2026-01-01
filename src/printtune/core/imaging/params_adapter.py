# src/printtune/core/imaging/params_adapter.py
from __future__ import annotations

from ..log_types import Candidate
from .transform import SimpleParams
from .parametric_linear import GlobalParams

def candidate_to_simple_params(c: Candidate) -> SimpleParams:
    if "oa_factors" in c.params:
        f = c.params["oa_factors"]
        return SimpleParams(
            brightness=float(f["f1"]),
            contrast=float(f["f2"]),
            color=float(f["f3"]),
        )
    x = c.params["x"]
    return SimpleParams(
        brightness=float(x["f1"]),
        contrast=float(x["f2"]),
        color=float(x["f3"]),
    )

def candidate_to_global_params(c: Candidate) -> GlobalParams:
    g = c.params["globals"]
    return GlobalParams(
        exposure_stops=float(g["exposure_stops"]),
        contrast=float(g["contrast"]),
        saturation=float(g["saturation"]),
        temp=float(g["temp"]),
        tint=float(g["tint"]),
        gamma=float(g["gamma"]),
    )