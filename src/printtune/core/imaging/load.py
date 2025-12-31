from pathlib import Path
from PIL import Image

def load_image_rgb(path: Path) -> Image.Image:
    img = Image.open(path)
    return img.convert("RGB")
