# src/printtune/core/optimizer/center.py
from __future__ import annotations

import torch
from ..log_types import SessionRecord
from .param_space_v1 import PARAM_KEYS_V1

def _candidate_to_x(c) -> list[float]:
    # c.params に {"globals": {...}} を入れる設計へ移行予定
    g = c.params.get("globals")
    if g is None:
        # 暫定互換（古いf1/f2等が残っている場合）
        raise ValueError("candidate params missing 'globals'")
    return [float(g[k]) for k in PARAM_KEYS_V1]

def extract_last_chosen_center(session: SessionRecord) -> torch.Tensor:
    # 直近の chosen が入ったラウンドを後ろから探す
    for rr in reversed(session.rounds):
        j = rr.judgment or {}
        if j.get("kind") == "chosen":
            chosen_slot = j["chosen_slot"]
            for c in rr.candidates:
                if c.slot == chosen_slot:
                    return torch.tensor(_candidate_to_x(c), dtype=torch.float)
    # fallback: 最終ラウンド先頭
    rr = session.rounds[-1]
    return torch.tensor(_candidate_to_x(rr.candidates[0]), dtype=torch.float)
