# app/pages/2_Final_Print.py
import io
import streamlit as st
from PIL import Image
from printtune.core.ui.streamlit_state import ensure_state
from printtune.core.io.paths import get_sample_image_path
from printtune.core.imaging.load import load_image_rgb
from printtune.core.imaging.parametric_linear import GlobalParams
from printtune.core.imaging.pipeline import render_image_with_global_params

st.set_page_config(page_title="Final Print", layout="wide")
ensure_state()

st.title("Final Print (PrintTune PoC)")

use_sample = st.toggle("sample.png を使う", value=True)
uploaded = None
if not use_sample:
    uploaded = st.file_uploader("PNGをアップロード", type=["png"])

if use_sample:
    img_in = load_image_rgb(get_sample_image_path())
else:
    if uploaded is None:
        st.stop()
    img_in = Image.open(io.BytesIO(uploaded.getvalue())).convert("RGB")

st.image(img_in, caption="Input", use_container_width=True)

# 暫定: identityパラメータ
params = GlobalParams()
img_out = render_image_with_global_params(img_in, params)
st.image(img_out, caption="Output (identity)", use_container_width=True)
