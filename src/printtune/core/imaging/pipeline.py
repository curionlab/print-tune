from dataclasses import dataclass
from PIL import Image
from .numpy_io import pil_to_rgb_u8, rgb_u8_to_pil
from .colorspace import srgb_u8_to_linear_f32, linear_f32_to_srgb_u8
from .parametric_linear import GlobalParams, apply_global_params_linear

@dataclass(frozen=True)
class RenderConfig:
    clip: bool = True

def render_image_with_global_params(img: Image.Image, params: GlobalParams, cfg: RenderConfig | None = None) -> Image.Image:
    _ = cfg
    rgb_u8 = pil_to_rgb_u8(img)
    lin = srgb_u8_to_linear_f32(rgb_u8)
    lin2 = apply_global_params_linear(lin, params)
    out_u8 = linear_f32_to_srgb_u8(lin2)
    return rgb_u8_to_pil(out_u8)
