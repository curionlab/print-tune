# app/pages/1_Run_Session.py
import streamlit as st

from printtune.core.io.paths import (
    get_sample_image_path,
    session_json_path,
    session_dir,
    artifacts_dir,
)
from printtune.core.io.session_store import save_session, load_session
from printtune.core.imaging.load import load_image_rgb
from printtune.core.session_runner import (
    new_session,
    create_round1,
    render_round_sheet,
    apply_judgment_chosen,
    apply_judgment_undecidable,
    apply_judgment_both_bad,
    append_round,
    create_round2_from_proposal,
)
from printtune.core.botorch.update_loop import propose_from_session
from printtune.core.ui.streamlit_state import ensure_state
from printtune.core.usecases import submit_judgment_and_maybe_create_next_round


st.set_page_config(page_title="Run Session", layout="wide")
ensure_state()
st.title("Run Session (PoC)")

# session_idはst.session_stateに保持（値型のみ）
if "session_id" not in st.session_state:
    st.session_state.session_id = None

if st.button("Start new session"):
    sess = new_session(sample_image_relpath="data/input/test_images/sample.png")
    rr1 = create_round1(sess)
    sess = append_round(sess, rr1)
    save_session(session_json_path(sess.session_id), sess)
    st.session_state.session_id = sess.session_id

sid = st.session_state.session_id
if sid is None:
    st.info("Start new session を押してください。")
    st.stop()

sess_path = session_json_path(sid)
sess = load_session(sess_path)

img = load_image_rgb(get_sample_image_path())
out_dir = artifacts_dir(sid)

# 現在ラウンド（最後）を表示
current = sess.rounds[-1]
sheet_path = render_round_sheet(img, current, out_dir=out_dir)
st.image(str(sheet_path), caption=f"Round{current.round_index} sheet", use_container_width=True)

slots = [c.slot for c in current.candidates]
kind = st.radio("判定", options=["chosen", "undecidable", "both_bad"], horizontal=True)

if kind == "chosen":
    chosen = st.radio("ベスト（slot）", options=slots, horizontal=True)

# （既存の kind/rubric UIの中に追加）
delta_scale = None
if kind in ("undecidable", "both_bad"):
    rubric = st.selectbox("観点（rubric）", ["overall","skin","neutral_gray","saturation","shadows","highlights"], key="rubric")
    if kind == "undecidable":
        next_action = st.radio("次アクション", options=["rejudge","reprint"], horizontal=True, key="next_action")
    else:
        next_action = "reprint"

    if next_action == "reprint":
        delta_scale = st.number_input(
            "reprint: delta_scale",
            min_value=1.0,
            max_value=3.0,
            value=1.5,
            step=0.25,
            format="%.2f",
            key="delta_scale",
        )

if st.button("Submit judgment"):
    sess = submit_judgment_and_maybe_create_next_round(
        sess,
        round_index=current.round_index,
        kind=kind,
        chosen_slot=(chosen if kind == "chosen" else None),
        rubric=(rubric if kind != "chosen" else None),
        next_action=(next_action if kind == "undecidable" else None),
        delta_scale=(float(delta_scale) if delta_scale is not None else 1.0),
    )
    save_session(sess_path, sess)
    st.success("Saved. (Next round may have been created.)")

st.divider()

# 次ラウンド提案
sess = load_session(sess_path)
can_propose = len(sess.comparisons_global) > 0
if can_propose and len(sess.rounds) < 5:
    if st.button("Propose next round (EUBO)"):
        proposal = propose_from_session(sess)
        next_index = len(sess.rounds) + 1
        rrn = create_round2_from_proposal(sess, proposal.X_next)
        # create_round2_from_proposalはround_index=2固定なので、ここで上書き（最小）
        rrn = rrn.__class__(**{**rrn.__dict__, "round_index": next_index})
        sess = append_round(sess, rrn)
        save_session(sess_path, sess)
        st.success(f"Added Round{next_index}.")
else:
    st.info("次ラウンド提案には、少なくとも1回の比較（chosen）が必要です。")
