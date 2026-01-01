# src/printtune/core/imaging/numpy_io.py
import numpy as np
from PIL import Image

def pil_to_rgb_u8(img: Image.Image) -> np.ndarray:
    # 常にRGB/uint8に正規化してからnumpyへ
    im = img.convert("RGB")
    arr = np.array(im, dtype=np.uint8) # HxWx3 uint8
    if arr.ndim != 3 or arr.shape[2] != 3:
        raise ValueError(f"Expected HxWx3, got {arr.shape}")
    return arr

def rgb_u8_to_pil(arr: np.ndarray) -> Image.Image:
    if arr.dtype != np.uint8:
        arr = arr.astype(np.uint8) # Pillowはuint8以外だと壊れやすい
    if arr.ndim != 3 or arr.shape[2] != 3:
        raise ValueError(f"Expected HxWx3, got {arr.shape}")
    return Image.fromarray(arr, mode="RGB")
