# src/printtune/core/optimizer/best_selector.py
from __future__ import annotations

import warnings

import torch
from ..log_types import SessionRecord
from .param_space_v1 import PARAM_KEYS_V1

def extract_last_chosen_globals(session: SessionRecord) -> dict:
    """
    最後に選択された候補のパラメータを返す（estimate_best_paramsのフォールバック用）
    """
    for rr in reversed(session.rounds):
        j = rr.judgment or {}
        if j.get("kind") == "chosen":
            slot = j["chosen_slot"]
            for c in rr.candidates:
                if c.slot == slot:
                    g = c.params["globals"]
                    return {k: float(g[k]) for k in PARAM_KEYS_V1}
                    
    # fallback: last round first candidate
    g = session.rounds[-1].candidates[0].params["globals"]
    return {k: float(g[k]) for k in PARAM_KEYS_V1}

def has_finalized_best_params(session: SessionRecord) -> bool:
    """
    セッションに確定したbest_paramsがあるかどうかを判定する。
    
    best_paramsが確定する条件:
    - 少なくとも1回の"chosen"判定が存在する
    
    Args:
        session: セッションレコード
        
    Returns:
        best_paramsが確定している場合True
    """
    for rr in session.rounds:
        j = rr.judgment or {}
        if j.get("kind") == "chosen":
            return True
    return False

def estimate_best_params(session: SessionRecord) -> dict[str, float]:
    """
    PairwiseGPの事後平均を最大化するパラメータを推定する。
    
    アプローチ:
    - 観測済み候補（train_X）の中で事後平均が最大のものを選ぶ
    - データ不足時は extract_last_chosen_globals にフォールバック
    
    注意:
    - chosen判定が存在しない場合、extract_last_chosen_globals()は
      最後のラウンドの最初の候補を返すが、これは「確定したbest」ではない
    - この関数は、chosen判定が存在する場合にのみ呼び出すべき
    
    Returns:
        globals形式のパラメータ辞書
    """
    # 比較データが存在しない場合は即座にフォールバック
    # comparisons_global が空、または候補が少なすぎる場合
    if not session.comparisons_global:
        return extract_last_chosen_globals(session)
    
    # すべてのラウンドの候補数を合計（train_Xのサイズ）
    total_candidates = sum(len(r.candidates) for r in session.rounds)
    if total_candidates < 2:
        return extract_last_chosen_globals(session)

    try:
        # 1. データ構築
        from ..botorch.build_data import build_torch_data
        data = build_torch_data(session)
        
        # 念のため再チェック（build_torch_data内でのデータ処理結果が空の可能性）
        if data.train_X.shape[0] < 2 or data.train_comp.shape[0] < 1:
            return extract_last_chosen_globals(session)

        # 2. GPモデル学習
        from ..botorch.pairwise_gp_fit import fit_pairwise_gp
        model = fit_pairwise_gp(data.train_X, data.train_comp)
        
        # 3. 事後平均の計算（方法A: 観測済み候補から選ぶ）
        with torch.no_grad():
            posterior = model.posterior(data.train_X)
            mean = posterior.mean
            mean_1d = mean.squeeze() #posterior.mean のshape揺れに備えて squeeze() してからargmax。
            best_idx = int(torch.argmax(mean_1d).item())
            best_X = data.train_X[best_idx]
        
        # 4. globals形式に変換
        return {k: float(best_X[i].item()) for i, k in enumerate(PARAM_KEYS_V1)}
        
    except Exception as e:
        # 数値計算エラー等の場合は安全にフォールバック
        warnings.warn(
            f"GP estimation failed ({type(e).__name__}: {e}), "
            f"falling back to last_chosen.",
            RuntimeWarning
        )
        return extract_last_chosen_globals(session)
