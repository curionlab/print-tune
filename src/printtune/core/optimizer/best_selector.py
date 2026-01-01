# src/printtune/core/optimizer/best_selector.py
from __future__ import annotations
import torch
from ..log_types import SessionRecord
from .center import extract_last_chosen_center
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
                    return dict(c.params["globals"])
    # fallback: last round first candidate
    return dict(session.rounds[-1].candidates[0].params["globals"])

def estimate_best_params(session: SessionRecord) -> dict:
    """
    PairwiseGPの事後平均を最大化するパラメータを推定する。
    
    アプローチ:
    - 観測済み候補（train_X）の中で事後平均が最大のものを選ぶ
    - データ不足時は extract_last_chosen_globals にフォールバック
    
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
            mean = posterior.mean  # shape: (N, 1)
            best_idx = torch.argmax(mean).item()
            best_X = data.train_X[best_idx]
        
        # 4. globals形式に変換
        best_dict = {}
        for i, key in enumerate(PARAM_KEYS_V1):
            best_dict[key] = float(best_X[i].item())
        
        return best_dict
        
    except Exception as e:
        # 数値計算エラー等の場合は安全にフォールバック
        import warnings
        warnings.warn(
            f"GP estimation failed ({type(e).__name__}: {e}), "
            f"falling back to last_chosen.",
            RuntimeWarning
        )
        return extract_last_chosen_globals(session)