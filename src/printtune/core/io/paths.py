# src/printtune/core/io/paths.py
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]

def get_sample_image_path() -> Path:
    return REPO_ROOT / "data" / "input" / "sample.png"

def sessions_root_dir() -> Path:
    return REPO_ROOT / "data" / "output" / "sessions"

def session_dir(session_id: str) -> Path:
    return sessions_root_dir() / session_id

def session_json_path(session_id: str) -> Path:
    return session_dir(session_id) / "session.json"

def artifacts_dir(session_id: str) -> Path:
    return session_dir(session_id) / "artifacts"

def best_params_json_path(session_id: str) -> Path:
    return session_dir(session_id) / "best_params.json"
