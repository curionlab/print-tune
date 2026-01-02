# app/pages/2_Final_Print.py
import io
from pathlib import Path
import streamlit as st
from PIL import Image
from printtune.core.ui.streamlit_state import ensure_state
from printtune.core.io.paths import get_sample_image_path, best_params_json_path, session_json_path
from printtune.core.io.best_params_store import save_best_params, load_best_params
from printtune.core.io.session_store import load_session
from printtune.core.imaging.load import load_image_rgb
from printtune.core.imaging.parametric_linear import GlobalParams
from printtune.core.imaging.pipeline import render_image_with_global_params
from printtune.core.imaging.globals_adapter import globals_dict_to_params
from printtune.core.imaging.upload import process_uploaded_image
from printtune.core.imaging.frame import compose_with_evaluation_frame
from printtune.core.ui.image_display import display_image_png
from printtune.core.optimizer.best_selector import has_finalized_best_params

st.set_page_config(page_title="Final Print", layout="wide")
ensure_state()

st.title("Final Print (PrintTune PoC)")

# セッションIDを取得
sid = st.session_state.get("session_id")

# セッションで使用した画像を取得（優先順位: session_state > セッションファイル > sample.png）
session_image = None
if sid:
    # セッションファイルから画像パスを取得
    sess_path = session_json_path(sid)
    if sess_path.exists():
        sess = load_session(sess_path)
        if sess.sample_image_relpath and sess.sample_image_relpath != "data/input/sample.png":
            # アップロード画像のパスが保存されている場合
            upload_path = Path(sess.sample_image_relpath)
            if upload_path.exists():
                session_image = load_image_rgb(upload_path)

# session_stateにアップロード画像がある場合は優先
if st.session_state.get("uploaded_image") is not None:
    session_image = st.session_state.uploaded_image

# use_sampleの状態をsession_stateから取得（初期化されていない場合はFalse）
if "use_sample" not in st.session_state:
    st.session_state.use_sample = False

# セッション画像がある場合は、use_sampleをFalseに設定（ユーザーが明示的にONにしない限り）
if session_image is not None:
    st.session_state.use_sample = False

# デフォルトはsample.pngを使わない（ユーザーが明示的にONにしない限り）
use_sample = st.toggle("sample.png を使う", value=st.session_state.use_sample, key="final_print_use_sample")
# トグルの状態をsession_stateに保存
st.session_state.use_sample = use_sample

uploaded = None
if not use_sample:
    uploaded = st.file_uploader("写真をアップロード（JPEG/PNG対応）", type=["jpg", "jpeg", "png"], key="final_print_upload")

# 画像を決定（優先順位: アップロード > セッション画像 > sample.png）
if not use_sample:
    if uploaded is not None:
        img_in = process_uploaded_image(uploaded)
    elif session_image is not None:
        img_in = session_image
    else:
        st.info("画像をアップロードするか、sample.pngを使用してください。")
        st.stop()
else:
    img_in = load_image_rgb(get_sample_image_path())

# ファイル名を生成（元のファイル名を使用）
input_filename = "sample"
if sid:
    # session_stateから元のファイル名を取得
    input_filename = st.session_state.get(f"original_filename_{sid}", "sample")
    # session_stateにない場合、セッションファイルから読み込んだ可能性があるので、パスから推測
    if input_filename == "sample":
        sess_path = session_json_path(sid)
        if sess_path.exists():
            sess = load_session(sess_path)
            if sess.sample_image_relpath and sess.sample_image_relpath != "data/input/sample.png":
                # 一時ファイル名からは元のファイル名を推測できないので、デフォルト値を使用
                pass

# PNG形式を保持したまま表示
display_image_png(img_in, caption="Input", width="stretch", download_filename=f"{input_filename}_input")

st.subheader("出力（印刷用）")

# best_paramsを取得
bp_path = None
if sid:
    bp_path = best_params_json_path(sid)

# 評価用フレームのON/OFF
use_frame = st.toggle("評価用フレームを適用", value=True, help="グレーグラデーションと原色パッチを追加します")

# best_paramsが確定しているかチェック（chosen判定が存在するか）
has_finalized = False
if sid:
    sess_path = session_json_path(sid)
    if sess_path.exists():
        sess = load_session(sess_path)
        has_finalized = has_finalized_best_params(sess)

if bp_path and bp_path.exists() and has_finalized:
    # ★ ここで毎回ロードすることで、Run Sessionでの更新を反映
    g = load_best_params(bp_path)
    best_params = globals_dict_to_params(g)
    
    st.caption(f"Applied Params: {g}") # デバッグ用に表示しても良い
    img_out = render_image_with_global_params(img_in, best_params)
    
    # 評価用フレームを適用
    if use_frame:
        img_out = compose_with_evaluation_frame(img_out)
    
    # ファイル名を生成
    frame_suffix = "_with_frame" if use_frame else ""
    final_filename = f"{input_filename}_final{frame_suffix}"
    
    # PNG形式を保持したまま表示
    display_image_png(img_out, caption="Final print image (Best Params Applied)", width="stretch", download_filename=final_filename)
    
    # ダウンロードボタン
    # PNG形式（可逆圧縮）で保存。JPEGアップロードでも圧縮劣化は発生しない
    buf = io.BytesIO()
    img_out.save(buf, format="PNG")
    st.download_button(
        "Download final_print.png",
        data=buf.getvalue(),
        file_name="final_print.png",
        mime="image/png",
    )
    
    # フレーム無し版もダウンロード可能にする
    if use_frame:
        img_out_no_frame = render_image_with_global_params(img_in, best_params)
        buf_no_frame = io.BytesIO()
        img_out_no_frame.save(buf_no_frame, format="PNG")
        st.download_button(
            "Download final_print_no_frame.png (フレーム無し)",
            data=buf_no_frame.getvalue(),
            file_name="final_print_no_frame.png",
            mime="image/png",
        )
else:
    st.warning("Best Params がまだありません。Run Session で判定を行ってください。")
    # 暫定（identity）表示
    params = GlobalParams()
    img_out = render_image_with_global_params(img_in, params)
    if use_frame:
        img_out = compose_with_evaluation_frame(img_out)
    # ファイル名を生成
    frame_suffix = "_with_frame" if use_frame else ""
    identity_filename = f"{input_filename}_identity{frame_suffix}"
    # PNG形式を保持したまま表示
    display_image_png(img_out, caption="Output (Identity / No Params)", width="stretch", download_filename=identity_filename)