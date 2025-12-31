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
    return lin ** g

def apply_temp_tint_linear_preserve_luma(lin: np.ndarray, temp: float, tint: float, eps: float = 1e-6) -> np.ndarray:
    t = float(temp)
    ti = float(tint)

    y_ref = luma709(lin)

    r_gain = 1.0 + 0.10 * t
    b_gain = 1.0 - 0.10 * t
    g_gain = 1.0 - 0.05 * ti  # 慎重なスタート

    out = lin.copy()
    out[..., 0] *= r_gain
    out[..., 1] *= g_gain
    out[..., 2] *= b_gain
    out = np.clip(out, 0.0, 1.0)

    y_new = luma709(out)
    s = y_ref / (y_new + eps)
    out *= s[..., None]
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
