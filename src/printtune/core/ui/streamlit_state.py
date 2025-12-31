# src/printtune/core/ui/streamlit_state.py
import streamlit as st

STATE_VERSION = 1

def ensure_state() -> None:
    if "state_version" not in st.session_state:
        st.session_state.state_version = STATE_VERSION
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
