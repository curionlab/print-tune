# src/printtune/core/imaging/sheet_layout.py
from __future__ import annotations

from dataclasses import dataclass
from PIL import Image, ImageDraw

@dataclass(frozen=True)
class SheetCell:
    slot: str
    candidate_id: str
    image: Image.Image  # RGB

def _fit_into(img: Image.Image, w: int, h: int) -> Image.Image:
    # アスペクト比を維持して枠に収める（thumbnailは比率を保つ）[web:457]
    canvas = Image.new("RGB", (w, h), (255, 255, 255))
    im = img.copy()
    im.thumbnail((w, h))
    x = (w - im.width) // 2
    y = (h - im.height) // 2
    canvas.paste(im, (x, y))
    return canvas

def render_sheet_2x2(cells: list[SheetCell], cell_w: int, cell_h: int, margin: int = 20) -> Image.Image:
    if len(cells) != 4:
        raise ValueError("cells must be 4 items (A-D).")

    sheet_w = margin * 3 + cell_w * 2
    sheet_h = margin * 3 + cell_h * 2
    sheet = Image.new("RGB", (sheet_w, sheet_h), (255, 255, 255))
    draw = ImageDraw.Draw(sheet)

    positions = [
        (margin, margin),
        (margin * 2 + cell_w, margin),
        (margin, margin * 2 + cell_h),
        (margin * 2 + cell_w, margin * 2 + cell_h),
    ]

    for cell, (x, y) in zip(cells, positions, strict=True):
        framed = _fit_into(cell.image, cell_w, cell_h)
        sheet.paste(framed, (x, y))
        label = f"{cell.slot} | {cell.candidate_id}"
        draw.text((x + 10, y + 10), label, fill=(0, 0, 0))  # Pillow標準のテキスト描画 [web:442]

    return sheet
