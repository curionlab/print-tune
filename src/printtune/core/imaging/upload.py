# src/printtune/core/imaging/upload.py
"""
画像アップロード処理のヘルパー関数
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from PIL import Image, ImageOps
from typing import Optional

def process_uploaded_image(uploaded_file) -> Image.Image:
    """
    アップロードされた画像を処理してRGB形式のPIL Imageに変換。
    
    Args:
        uploaded_file: StreamlitのUploadedFileオブジェクト
        
    Returns:
        RGB形式のPIL Image（EXIF orientation適用済み）
    """
    img = Image.open(uploaded_file)
    # EXIF orientationを適用
    img = ImageOps.exif_transpose(img)
    # RGBに変換（JPEG/PNG両対応）
    img = img.convert("RGB")
    return img

def save_uploaded_image_to_temp(img: Image.Image, session_id: str) -> Path:
    """
    アップロード画像を一時ファイルとして保存。
    
    注意: JPEGをアップロードしても、PNG形式（可逆圧縮）で保存するため、
    圧縮劣化は発生しません。JPEGの非可逆圧縮による劣化は1回のみ（アップロード時のデコード）です。
    
    Args:
        img: PIL Image
        session_id: セッションID（ファイル名に使用）
        
    Returns:
        保存先のPath
    """
    temp_dir = Path(tempfile.gettempdir()) / "printtune_uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # セッションIDをファイル名に使用（拡張子はPNG固定）
    # PNGは可逆圧縮なので、JPEGアップロード後の再保存でも劣化しない
    temp_path = temp_dir / f"{session_id}_upload.png"
    img.save(temp_path, format="PNG")
    return temp_path

