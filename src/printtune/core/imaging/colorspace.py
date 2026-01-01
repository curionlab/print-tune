# src/printtune/core/imaging/colorspace.py
import numpy as np

def srgb_u8_to_linear_f32(rgb_u8: np.ndarray) -> np.ndarray:
    """
    rgb_u8: HxWx3 uint8 (0..255)
    returns: HxWx3 float32 (0..1) linear light
    """
    x = rgb_u8.astype(np.float32) / 255.0
    lin = np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
    return lin.astype(np.float32)

def linear_f32_to_srgb_u8(lin: np.ndarray) -> np.ndarray:
    """
    lin: HxWx3 float32 (0..1) linear light
    returns: HxWx3 uint8 (0..255) sRGB encoded
    """
    lin = np.clip(lin, 0.0, 1.0).astype(np.float32)
    x = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * (lin ** (1 / 2.4)) - 0.055)
    x = np.clip(x, 0.0, 1.0)
    return (x * 255.0 + 0.5).astype(np.uint8)