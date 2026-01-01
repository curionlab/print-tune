# src/printtune/core/botorch/update_loop.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import torch

from ..log_types import SessionRecord
from ..optimizer.param_space_v1 import PARAM_KEYS_V1
from ..optimizer.best_selector import estimate_best_params
from ..policy_axes import schedule_for_round
from .build_data import build_torch_data
from .pairwise_gp_fit import fit_pairwise_gp
from .propose_next import propose_next_pair


@dataclass(frozen=True)
class NextProposal:
    X_next: list[list[float]]
    schedule: dict


def _keys_to_mask(active_keys: list[str]) -> torch.Tensor:
    active = set(active_keys)
    return torch.tensor([k in active for k in PARAM_KEYS_V1], dtype=torch.bool)


def _center_tensor_from_session(session: SessionRecord) -> torch.Tensor:
    g_best = estimate_best_params(session)
    center_list = [float(g_best[k]) for k in PARAM_KEYS_V1]
    return torch.tensor(center_list, dtype=torch.float)


def _fallback_reprint_x(
    session: SessionRecord,
    phase_round_index: int,
    rubric: Optional[str],
    delta_scale: float,
    q: int,
) -> NextProposal:
    """
    GP学習に必要な比較データが不足している場合のフォールバック。
    - schedule（active_keys/delta/micro_ratio）は残す（可観測性を優先）
    - Xは「中心の1軸だけを±deltaで動かす」簡易生成
    """
    sched = schedule_for_round(phase_round_index, rubric=rubric)
    center = _center_tensor_from_session(session).tolist()

    delta = float(sched.delta) * float(delta_scale)

    # まずは exposure_stops を優先し、無ければ先頭のactive_keyを使う
    shift_key = "exposure_stops"
    if shift_key not in list(sched.active_keys) and len(list(sched.active_keys)) > 0:
        shift_key = list(sched.active_keys)[0]

    key_to_index = {k: i for i, k in enumerate(PARAM_KEYS_V1)}
    idx = key_to_index.get(shift_key, 0)

    def clamp(v: float) -> float:
        return max(-2.0, min(2.0, v))

    X_next: list[list[float]] = []
    for sign in (+1.0, -1.0):
        x = [float(v) for v in center]
        x[idx] = clamp(x[idx] + sign * delta)
        X_next.append(x)

    if q == 4:
        # 追加でもう1軸（可能なら2番目のactive_key）も動かして4点にする
        idx2 = idx
        active_list = list(sched.active_keys)
        if len(active_list) >= 2:
            idx2 = key_to_index.get(active_list[1], idx)

        for sign in (+1.0, -1.0):
            x = [float(v) for v in center]
            x[idx2] = clamp(x[idx2] + sign * delta)
            X_next.append(x)

    X_next = X_next[:q]

    return NextProposal(
        X_next=X_next,
        schedule={
            "active_keys": list(sched.active_keys),
            "delta": float(sched.delta),
            "micro_ratio": float(sched.micro_ratio),
            "delta_scale": float(delta_scale),
            "center_source": "fallback_no_comparison",
        },
    )


def propose_from_session_for_round(
    session: SessionRecord,
    phase_round_index: int,
    rubric: Optional[str] = None,
) -> NextProposal:
    """
    次のpairwise提案（探索）を返す。

    Args:
        session: セッション。
        phase_round_index: 「実ラウンド番号」ではなく「スケジュール段階(phase)」。
        rubric: 観点。

    Returns:
        NextProposal。
    """
    data = build_torch_data(session)
    model = fit_pairwise_gp(data.train_X, data.train_comp)

    sched = schedule_for_round(phase_round_index, rubric=rubric)
    center = _center_tensor_from_session(session)

    mask = _keys_to_mask(list(sched.active_keys))

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
            "delta": float(sched.delta),
            "micro_ratio": float(sched.micro_ratio),
            "center_source": "posterior_mean",
        },
    )


def propose_reprint_pair(
    session: SessionRecord,
    phase_round_index: int,
    rubric: Optional[str] = None,
    delta_scale: float = 1.5,
    q: int = 2,
    seed: Optional[int] = None,
) -> NextProposal:
    """
    Reprint用の提案: 現在のcenter周辺で探索幅を広げて再提案。

    Args:
        session: セッション。
        phase_round_index: スケジュール段階(phase)。
        rubric: 観点。
        delta_scale: schedule.delta に掛ける倍率（探索幅の拡大率）。
        q: 提案点数（pairwiseは2、OAは4など）。
        seed: 再現性用の乱数seed（torch.manual_seedに設定）。

    Returns:
        NextProposal。
    """
    if seed is not None:
        torch.manual_seed(int(seed))

    sched = schedule_for_round(phase_round_index, rubric=rubric)
    scaled_delta = float(sched.delta) * float(delta_scale)

    try:
        data = build_torch_data(session)
    except ValueError:
        return _fallback_reprint_x(
            session=session,
            phase_round_index=phase_round_index,
            rubric=rubric,
            delta_scale=delta_scale,
            q=q,
        )

    model = fit_pairwise_gp(data.train_X, data.train_comp)
    center = _center_tensor_from_session(session)
    mask = _keys_to_mask(list(sched.active_keys))

    proposed = propose_next_pair(
        model,
        center=center,
        active_mask=mask,
        delta=scaled_delta,
        micro_ratio=sched.micro_ratio,
        q=q,
    )

    X_next = proposed.X_next.detach().cpu().tolist()

    return NextProposal(
        X_next=X_next,
        schedule={
            "active_keys": list(sched.active_keys),
            "delta": float(sched.delta),
            "micro_ratio": float(sched.micro_ratio),
            "delta_scale": float(delta_scale),
            "center_source": "posterior_mean",
            "seed": seed,
        },
    )
