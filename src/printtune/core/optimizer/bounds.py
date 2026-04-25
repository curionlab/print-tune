# src/printtune/core/optimizer/bounds.py
from __future__ import annotations
import torch
from .param_space_v1 import PARAM_KEYS_V1

def default_bounds(d: int) -> torch.Tensor:
    # PARAM_KEYS_V1 の並び順に合わせたbounds定義
    # "exposure_stops", "contrast", "saturation", "temp", "tint", "gamma"
    
    # exposure: [-1, 1] (±1 stop)
    # contrast/sat/gamma: [-0.25, 0.25] (0.75~1.25倍)
    # temp/tint: [-10, 10] (WB補正用、実測±5が見える範囲なので広めに)
    
    bounds_map = {
        "exposure_stops": 1.0,
        "contrast": 0.25,
        "saturation": 0.25,
        "temp": 10.0,
        "tint": 10.0,
        "gamma": 0.25,
    }
    
    # dがPARAM_KEYS_V1長と一致しない場合のガードが必要だが、
    # いったんはキー順序依存で生成
    if d != len(PARAM_KEYS_V1):
        # 万一不一致なら安全側で狭く一律生成
        return torch.stack([torch.full((d,), -0.2), torch.full((d,), 0.2)], dim=0)

    los = []
    his = []
    for k in PARAM_KEYS_V1:
        lim = bounds_map.get(k, 0.2)
        los.append(-lim)
        his.append(lim)
        
    return torch.stack([torch.tensor(los), torch.tensor(his)], dim=0)
