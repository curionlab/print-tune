# src/printmatch/core/imaging/globals_adapter.py
from __future__ import annotations
from .parametric_linear import GlobalParams

def globals_dict_to_params(g: dict) -> GlobalParams:
    return GlobalParams(
        exposure_stops=float(g["exposure_stops"]),
        contrast=float(g["contrast"]),
        saturation=float(g["saturation"]),
        temp=float(g["temp"]),
        tint=float(g["tint"]),
        gamma=float(g["gamma"]),
    )
