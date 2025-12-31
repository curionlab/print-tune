# src/printtune/core/imaging/transform.py
from __future__ import annotations

from dataclasses import dataclass
from PIL import Image, ImageEnhance

@dataclass(frozen=True)
class SimpleParams:
    # いずれも 0.0 が中立、範囲は大体 [-1, +1] を想定
    brightness: float
    contrast: float
    color: float  # saturation相当

def _to_factor(x: float, scale: float = 0.35) -> float:
    # enhance() の factor は 1.0 が中立 [web:521]
    # x=-1..+1 を 1±scale にマップ
    return float(1.0 + scale * x)

def apply_simple_transform(img: Image.Image, p: SimpleParams) -> Image.Image:
    out = img
    out = ImageEnhance.Brightness(out).enhance(_to_factor(p.brightness))
    out = ImageEnhance.Contrast(out).enhance(_to_factor(p.contrast))
    out = ImageEnhance.Color(out).enhance(_to_factor(p.color))
    return out
