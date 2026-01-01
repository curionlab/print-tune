# src/printtune/core/botorch/update_loop.py
from __future__ import annotations

from dataclasses import dataclass

import torch

from ..optimizer.bounds import default_bounds
from .build_data import build_torch_data
from .pairwise_gp_fit import fit_pairwise_gp
from .propose_next import propose_next_pair
from ..policy_axes import schedule_for_round
from ..optimizer.param_space_v1 import PARAM_KEYS_V1
from ..optimizer.best_selector import extract_last_chosen_globals

@dataclass(frozen=True)
class NextProposal:
    X_next: list[list[float]]  # python listへ戻す（UI/ログで扱いやすく）
    schedule: dict

def _keys_to_mask(active_keys: list[str]) -> torch.Tensor:
    active = set(active_keys)
    return torch.tensor([k in active for k in PARAM_KEYS_V1], dtype=torch.bool)

def propose_from_session_for_round(session, next_round_index: int) -> NextProposal:
    # 1. GP学習データの構築
    data = build_torch_data(session)
    model = fit_pairwise_gp(data.train_X, data.train_comp)

    # 2. スケジュールとセンターの決定
    sched = schedule_for_round(next_round_index)
    
    # center抽出: extract_last_chosen_globals は dict を返すので list[float] に変換
    g_best = extract_last_chosen_globals(session)
    center_list = [float(g_best[k]) for k in PARAM_KEYS_V1]
    center = torch.tensor(center_list, dtype=torch.float)

    # 3. マスク作成
    mask = _keys_to_mask(list(sched.active_keys))

    # 4. 提案（スケジュール拘束付き）
    proposed = propose_next_pair(
        model,
        center=center,
        active_mask=mask,
        delta=sched.delta,
        micro_ratio=sched.micro_ratio,
        q=2,
    )

    X_next = proposed.X_next.detach().cpu().tolist()
    
    return NextProposal(
        X_next=X_next,
        schedule={
            "active_keys": list(sched.active_keys), 
            "delta": sched.delta, 
            "micro_ratio": sched.micro_ratio,
            "center_source": "last_chosen"
        },
    )


#---以下削除
from ..optimizer.bounds import default_bounds

def propose_from_session(session) -> NextProposal:
    data = build_torch_data(session)
    model = fit_pairwise_gp(data.train_X, data.train_comp)
    bounds = default_bounds(d=data.train_X.shape[-1])
    proposed = propose_next_pair(model, bounds=bounds, q=2)
    X_next = proposed.X_next.detach().cpu().tolist()
    return NextProposal(X_next=X_next)

