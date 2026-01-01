# app/pages/2_Final_Print.py
import io
import streamlit as st
from PIL import Image
from printtune.core.ui.streamlit_state import ensure_state
from printtune.core.io.paths import get_sample_image_path, best_params_json_path
from printtune.core.io.best_params_store import save_best_params, load_best_params
from printtune.core.imaging.load import load_image_rgb
from printtune.core.imaging.parametric_linear import GlobalParams
from printtune.core.imaging.pipeline import render_image_with_global_params
from printtune.core.imaging.globals_adapter import globals_dict_to_params

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

st.image(img_in, caption="Input", width='stretch')


st.subheader("出力（印刷用）")

# session_id が必要なので取得
sid = st.session_state.get("session_id")
bp_path = None
if sid:
    bp_path = best_params_json_path(sid)

if bp_path and bp_path.exists():
    # ★ ここで毎回ロードすることで、Run Sessionでの更新を反映
    g = load_best_params(bp_path)
    best_params = globals_dict_to_params(g)
    
    st.caption(f"Applied Params: {g}") # デバッグ用に表示しても良い
    img_out = render_image_with_global_params(img_in, best_params)
    
    st.image(img_out, caption="Final print image (Best Params Applied)", width='stretch')
    
    # ... (ダウンロードボタン) ...
else:
    st.warning("Best Params がまだありません。Run Session で判定を行ってください。")
    # 暫定（identity）表示
    params = GlobalParams()
    img_out = render_image_with_global_params(img_in, params)
    st.image(img_out, caption="Output (Identity / No Params)", width='stretch')