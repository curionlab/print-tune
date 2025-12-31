from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]

def get_sample_image_path() -> Path:
    return REPO_ROOT / "data" / "input" / "test_images" / "sample.png"

def sessions_root_dir() -> Path:
    return REPO_ROOT / "data" / "output" / "sessions"

def session_dir(session_id: str) -> Path:
    return sessions_root_dir() / session_id
