# src/printtune/core/imaging/parametric_linear.py
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class GlobalParams:
    exposure_stops: float = 0.0
    contrast: float = 1.0
    saturation: float = 1.0
    temp: float = 0.0
    tint: float = 0.0
    gamma: float = 1.0

def luma709(lin: np.ndarray) -> np.ndarray:
    # Linear RGBでの相対輝度（sRGB/Rec.709の係数）
    return 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]

def apply_exposure_linear(lin: np.ndarray, exposure_stops: float) -> np.ndarray:
    return lin * (2.0 ** float(exposure_stops))

def apply_contrast_linear(lin: np.ndarray, contrast: float) -> np.ndarray:
    c = float(contrast)
    pivot = 0.18
    return (lin - pivot) * c + pivot

def apply_saturation_linear(lin: np.ndarray, saturation: float) -> np.ndarray:
    s = float(saturation)
    y = luma709(lin)[..., None]
    return y + (lin - y) * s

def apply_gamma_linear(lin: np.ndarray, gamma: float) -> np.ndarray:
    g = float(gamma)
    lin = np.clip(lin, 0.0, None)
    # g>1で暗部圧縮、g<1で暗部持ち上げ（暫定）
    return lin ** g

def apply_temp_tint_linear_preserve_luma(lin: np.ndarray, temp: float, tint: float, eps: float = 1e-6) -> np.ndarray:
    # 暫定実装：チャネルゲインでWB近似 → Y保存で戻す
    # temp/tintの係数（0.10/0.08）は暫定です。
    # ここは「印象が自然か」「探索幅に対して敏感すぎないか」を見ながら調整する領域
    # temp: +で暖色（R↑B↓）、tint: +でマゼンタ（G↓）
    t = float(temp)
    ti = float(tint)

    y_ref = luma709(lin)

    r_gain = 1.0 + 0.10 * t
    b_gain = 1.0 - 0.10 * t
    g_gain = 1.0 - 0.05 * ti  # まずは控えめに開始（必要なら0.08へ）

    out = lin.copy()
    out[..., 0] *= r_gain
    out[..., 1] *= g_gain
    out[..., 2] *= b_gain

    # 高彩度原色での破綻を抑える：Y保存の前にも一度クリップ
    out = np.clip(out, 0.0, 1.0)

    y_new = luma709(out)
    s = y_ref / (y_new + eps)
    out *= s[..., None]

    # 最終段でも必ずクリップ（出力直前の安全策）
    out = np.clip(out, 0.0, 1.0)
    return out

def apply_global_params_linear(lin: np.ndarray, p: GlobalParams) -> np.ndarray:
    out = lin
    out = apply_exposure_linear(out, p.exposure_stops)
    out = apply_contrast_linear(out, p.contrast)
    out = apply_temp_tint_linear_preserve_luma(out, p.temp, p.tint)
    out = apply_saturation_linear(out, p.saturation)
    out = apply_gamma_linear(out, p.gamma)
    return out
