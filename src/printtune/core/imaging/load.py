# src/printtune/core/imaging/load.py
from pathlib import Path
from PIL import Image

def load_image_rgb(path: Path) -> Image.Image:
    # PNG-24想定でも、内部処理はRGBに正規化（将来は管理を追加）
    img = Image.open(path)
    return img.convert("RGB")
