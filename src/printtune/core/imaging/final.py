# src/printmatch/core/imaging/final.py
from __future__ import annotations

from PIL import Image
from .parametric_linear import GlobalParams
from .pipeline import render_image_with_global_params

def render_final_image(img: Image.Image, best_params: GlobalParams) -> Image.Image:
    return render_image_with_global_params(img, best_params)
