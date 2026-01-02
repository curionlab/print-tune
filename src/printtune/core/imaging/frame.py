# src/printtune/core/imaging/frame.py
"""
評価用フレーム（グレーグラデーション＋原色パッチ）の合成処理
"""
from __future__ import annotations

from PIL import Image, ImageDraw

def compose_with_evaluation_frame(photo: Image.Image) -> Image.Image:
    """
    写真の周囲にグレーグラデーションと原色パッチを付けた評価用画像を返す。
    
    レイアウト:
    - 上辺: 横長のグレーグラデーション（左:黒→右:白）
    - 左辺: 縦に R, G, B のパッチ
    - 右辺: 縦に C, M, Y, neutral gray (50%) のパッチ
    
    Args:
        photo: 元の写真（PIL Image）
        
    Returns:
        フレーム付き画像
    """
    # フレーム幅を決定（写真の短辺の10-15%程度）
    short_side = min(photo.width, photo.height)
    frame_width = max(40, int(short_side * 0.12))  # 最小40px
    
    # パッチサイズ（正方形）
    patch_size = frame_width
    
    # キャンバスサイズを計算
    canvas_w = photo.width + 2 * frame_width
    canvas_h = photo.height + frame_width  # 上辺のみ追加
    
    # 白地のキャンバスを作成
    canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
    
    # 写真を中央に配置
    photo_x = frame_width
    photo_y = frame_width
    canvas.paste(photo, (photo_x, photo_y))
    
    draw = ImageDraw.Draw(canvas)
    
    # 1. 上辺: グレーグラデーション（横ストリップ）
    grad_y = 0
    grad_h = frame_width
    for x in range(photo_x, photo_x + photo.width):
        # 0 (黒) → 255 (白) の線形グラデーション
        gray_value = int(255 * (x - photo_x) / photo.width)
        draw.rectangle(
            [(x, grad_y), (x + 1, grad_y + grad_h)],
            fill=(gray_value, gray_value, gray_value)
        )
    
    # 2. 左辺: R, G, B パッチ（縦に配置）
    left_x = 0
    patches_per_side = 3  # R, G, B
    patch_spacing = (photo.height - patches_per_side * patch_size) // (patches_per_side + 1)
    
    left_patches = [
        (255, 0, 0),    # R
        (0, 255, 0),    # G
        (0, 0, 255),    # B
    ]
    
    for i, color in enumerate(left_patches):
        patch_y = photo_y + patch_spacing + i * (patch_size + patch_spacing)
        draw.rectangle(
            [(left_x, patch_y), (left_x + patch_size, patch_y + patch_size)],
            fill=color
        )
    
    # 3. 右辺: C, M, Y, neutral gray パッチ（縦に配置）
    right_x = photo_x + photo.width
    patches_per_side_right = 4  # C, M, Y, Gray
    patch_spacing_right = (photo.height - patches_per_side_right * patch_size) // (patches_per_side_right + 1)
    
    right_patches = [
        (0, 255, 255),      # C
        (255, 0, 255),      # M
        (255, 255, 0),       # Y
        (128, 128, 128),     # Neutral gray (50%)
    ]
    
    for i, color in enumerate(right_patches):
        patch_y = photo_y + patch_spacing_right + i * (patch_size + patch_spacing_right)
        draw.rectangle(
            [(right_x, patch_y), (right_x + patch_size, patch_y + patch_size)],
            fill=color
        )
    
    return canvas

