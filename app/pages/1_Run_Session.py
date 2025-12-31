import streamlit as st
from printtune.core.ui.streamlit_state import ensure_state
from printtune.core.io.paths import get_sample_image_path
from printtune.core.imaging.load import load_image_rgb

st.set_page_config(page_title="Run Session", layout="wide")
ensure_state()

st.title("Run Session (PrintTune PoC)")

img = load_image_rgb(get_sample_image_path())
st.image(img, caption=f"Sample ({img.width}x{img.height})", use_container_width=True)
