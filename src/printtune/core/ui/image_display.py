# src/printtune/core/ui/image_display.py
"""
PNG形式を保持したまま画像を表示するヘルパー関数
Streamlitのst.image()は画像をJPEGに変換することがあるため、
Base64エンコードしてHTMLで直接表示することでPNG形式を保持する
"""
from __future__ import annotations

import base64
import io
from PIL import Image
import streamlit as st

def display_image_png(img: Image.Image, caption: str = "", width: str = "stretch", download_filename: str | None = None) -> None:
    """
    PNG形式を保持したまま画像を表示する。
    
    Streamlitのst.image()は大きな画像をJPEGに変換することがあるため、
    Base64エンコードしてHTMLで直接表示することでPNG形式を保持する。
    
    Args:
        img: PIL Image
        caption: キャプション
        width: 表示幅（"stretch" または数値）
        download_filename: 右クリックで保存した時のファイル名（例: "sample_round1.png"）
    """
    # PNG形式でBytesIOに保存
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    
    # Base64エンコード
    img_base64 = base64.b64encode(buf.getvalue()).decode()
    
    # HTMLで表示（PNG形式を保持）
    width_style = f"width: {width}px;" if isinstance(width, (int, float)) else "width: 100%;"
    
    # download属性を設定するために<a>タグでラップ
    if download_filename:
        # ファイル名に拡張子がない場合は追加
        if not download_filename.endswith('.png'):
            download_filename = f"{download_filename}.png"
        html = f"""
        <div style="text-align: center;">
            <a href="data:image/png;base64,{img_base64}" download="{download_filename}" style="display: inline-block;">
                <img src="data:image/png;base64,{img_base64}" style="{width_style}" alt="{caption}">
            </a>
            {f'<p style="text-align: center; color: #666; font-size: 0.9em;">{caption}</p>' if caption else ''}
        </div>
        """
    else:
        html = f"""
        <div style="text-align: center;">
            <img src="data:image/png;base64,{img_base64}" style="{width_style}" alt="{caption}">
            {f'<p style="text-align: center; color: #666; font-size: 0.9em;">{caption}</p>' if caption else ''}
        </div>
        """
    st.markdown(html, unsafe_allow_html=True)

