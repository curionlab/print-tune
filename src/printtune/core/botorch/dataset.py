# src/printtune/core/botorch/dataset.py
from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class PreferenceDataset:
    X: list[list[float]]           # n x d（後でtorch tensor化）
    comps: list[list[int]]         # m x 2（winner, loser）
    candidate_ids: list[str]       # index→candidate_id

def build_comparisons_from_choice(winner_index: int, n_items: int) -> list[list[int]]:
    # 4択のchosenを「winner vs その他全部」へ展開
    comps: list[list[int]] = []
    for j in range(n_items):
        if j == winner_index:
            continue
        comps.append([winner_index, j])
    return comps
