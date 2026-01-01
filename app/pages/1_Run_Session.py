# app/pages/1_Run_Session.py
import io
import time
from PIL import Image
import streamlit as st

from printtune.core.io.paths import (
    get_sample_image_path,
    session_json_path,
    session_dir,
    artifacts_dir,
    best_params_json_path,
)
from printtune.core.io.session_store import save_session, load_session
from printtune.core.io.best_params_store import save_best_params, load_best_params
from printtune.core.optimizer.best_selector import estimate_best_params
from printtune.core.imaging.globals_adapter import globals_dict_to_params
from printtune.core.imaging.load import load_image_rgb
from printtune.core.imaging.pipeline import render_image_with_global_params
from printtune.core.session_runner import (
    new_session,
    create_round1,
    render_round_sheet,
    append_round,
)
from printtune.core.botorch.update_loop import propose_from_session_for_round
from printtune.core.ui.streamlit_state import ensure_state
from printtune.core.usecases import submit_judgment_and_maybe_create_next_round
from printtune.core.session_loop import make_next_round # 直接呼び出し用にimport

# 定数: 最大ラウンド数（reprint等で増えることを考慮して少し多めに）

MAX_ROUNDS = 10
STANDARD_ROUNDS = 5 # ひとまずの目安

st.set_page_config(page_title="Run Session", layout="wide")
ensure_state()
st.title("Run Session (PoC)")

# --- Session Management ---
if "session_id" not in st.session_state:
    st.session_state.session_id = None

if st.button("Start new session"):
    sess = new_session(sample_image_relpath="data/input/test_images/sample.png")
    rr1 = create_round1(sess)
    sess = append_round(sess, rr1)
    save_session(session_json_path(sess.session_id), sess)
    st.session_state.session_id = sess.session_id
    st.rerun()

sid = st.session_state.session_id
if sid is None:
    st.info("Start new session を押してください。")
    st.stop()

sess_path = session_json_path(sid)
sess = load_session(sess_path)

img = load_image_rgb(get_sample_image_path())
out_dir = artifacts_dir(sid)

# --- Target Image Display ---
# ユーザーが目指すべき「正解（画面上の見た目）」を常に表示
st.subheader("Target (Original Screen View)")
st.caption("この画面上の見た目に合うように、印刷結果を選んでください。")
# 画面占有率を下げるため、少し小さめに表示するか、カラムを切る
col_orig, _ = st.columns([1, 2])
with col_orig:
    st.image(img, caption="Original Image", width='stretch')

st.divider()

# --- Current Round Display ---
current = sess.rounds[-1]
sheet_path = out_dir / f"round{current.round_index:02d}_sheet.png"
if not sheet_path.exists():
    sheet_path = render_round_sheet(img, current, out_dir=out_dir)

st.subheader(f"Current Round: {current.round_index}")
st.image(str(sheet_path), caption=f"Round{current.round_index} sheet (Print Candidates)", width='stretch')

with st.expander("Show Round Details (Debug Info)"):
    st.json({
        "round_index": current.round_index,
        "mode": current.mode,
        "purpose": current.purpose,
        "meta": current.meta,
    })

# --- Judgment UI (Formを廃止してインタラクティブに) ---
is_judged = current.judgment is not None

if is_judged:
    st.success("このラウンドは判定済みです。")
    # 次のラウンドがあればそちらへ進むボタン、なければ終了案内
    if current.round_index >= len(sess.rounds):
         st.info("次のラウンド生成待ち、または終了です。")
else:
    st.write("### Judgment")
    
    # st.form を廃止し、条件分岐が即座にUIに反映されるようにする
    slots = [c.slot for c in current.candidates]
    kind = st.radio("判定タイプ", options=["chosen", "undecidable", "both_bad"], horizontal=True, key=f"kind_{current.round_index}")

    chosen = None
    rubric = None
    next_action = None
    delta_scale = None
    
    # UIの条件分岐表示
    if kind == "chosen":
        chosen = st.radio("ベスト（slot）", options=slots, horizontal=True, key=f"chosen_{current.round_index}")
        
    elif kind in ("undecidable", "both_bad"):
        rubric = st.selectbox("観点（rubric）", ["overall","skin","neutral_gray","saturation","shadows","highlights"], key=f"rubric_{current.round_index}")
        
        if kind == "undecidable":
            # undecidableの場合のネクストアクション
            # rejudge: 今の候補の中から強引に選ぶ（あるいは見直す）
            # reprint: 探索幅を広げてやり直す
            next_action = st.radio("次アクション", options=["rejudge", "reprint"], horizontal=True, key=f"action_{current.round_index}")
        else:
            # both_bad は問答無用で reprint (探索やり直し)
            next_action = "reprint" # both_bad
            st.warning("both_bad: Reprint (探索幅を広げて再生成) します。")

        # Actionごとの追加入力
        if next_action == "reprint":
            delta_scale = st.number_input(
                "reprint: delta_scale (探索幅の拡大率)",
                min_value=1.0, max_value=3.0, value=1.5, step=0.25, format="%.2f",
                key=f"delta_{current.round_index}"
            )
        else: # rejudge
        # Rejudgeの場合、結局「どれが良いか」を選ばせる（判定を強制）
            st.info("Rejudge: 違いの目立つ観点（Rubric）を指定して、近いものを選んで次に進みます。")
            chosen = st.radio("ベスト（slot）", options=slots, horizontal=True, key=f"chosen_{current.round_index}_rejudge")
   

    # アクションボタン
    btn_label = "決定して次へ進む"
    if kind == "chosen" or (next_action == "rejudge"):
        btn_label = "決定 (Next Proposal)"
    elif next_action == "reprint":
        btn_label = "決定 (Reprint)"

    if st.button(btn_label, type="primary"):
        # 1. 判定保存 & 次ラウンド生成 (全てusecasesに委譲)
        # Spinnerを出して処理中であることを示す
        with st.spinner("Processing judgment & calculating next proposal..."):
            sess = submit_judgment_and_maybe_create_next_round(
                sess,
                round_index=current.round_index,
                kind=kind,
                chosen_slot=chosen,
                rubric=rubric,
                next_action=next_action,
                delta_scale=(float(delta_scale) if delta_scale is not None else 1.0),
            )
        
        # (以前の if kind == "chosen": make_next_round... ブロックは削除)
        
        if len(sess.rounds) >= 10: # MAX_ROUNDS定数参照推奨
                st.warning("最大ラウンド数に達しました。")

        # 2. 保存 & Best Params 更新 & リロード
        save_session(sess_path, sess)
        g = estimate_best_params(sess)
        save_best_params(best_params_json_path(sid), g)
        st.success("Saved. Reloading...")
        time.sleep(0.5)
        st.rerun()

# --- Round終了案内 ---
if len(sess.rounds) >= STANDARD_ROUNDS:
    st.divider()
    st.success(f"🎉 標準ラウンド数（{STANDARD_ROUNDS}回）に到達しました！")
    st.markdown("""
    **ここまでの結果で良ければ、Final Print へ進んで印刷用画像を出力してください。**
    
    まだ満足できない場合は、続けて判定を行うことも可能です（最大10回まで）。
    """)
    if st.button("Go to Final Print ページへ移動するイメージ"):
        st.switch_page("pages/2_Final_Print.py") # Streamlitのページ遷移機能

st.divider()

# --- Robustness check ---
st.subheader("Verification & Download")

# best params の手動保存ボタン（自動保存を入れたので必須ではないが、明示的にやりたい場合用）
if st.button("Force save current best params"):
    g = estimate_best_params(sess)
    save_best_params(best_params_json_path(sid), g)
    st.success("Best params updated.")

# 検証画像アップロード
uploaded = st.file_uploader("検証画像（PNG）をアップロード", type=["png"], key="verify_png")
if uploaded is not None:
    img_verify = Image.open(io.BytesIO(uploaded.getvalue())).convert("RGB")
    st.image(img_verify, caption="Verify input", width='stretch')

    bp_path = best_params_json_path(sid)
    if bp_path.exists():
        g = load_best_params(bp_path)
        params = globals_dict_to_params(g)
        out_img = render_image_with_global_params(img_verify, params)
        st.image(out_img, caption="Verify output (current best)", width='stretch')

        buf = io.BytesIO()
        out_img.save(buf, format="PNG")
        st.download_button(
            "Download verify_best.png",
            data=buf.getvalue(),
            file_name="verify_best.png",
            mime="image/png",
        )
    else:
        st.info("まだBest Paramsが保存されていません（一度判定を行うと保存されます）。")
