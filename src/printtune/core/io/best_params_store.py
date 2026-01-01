# src/printtune/core/io/best_params_store.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

def save_best_params(path: Path, globals_params: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(globals_params, f, ensure_ascii=False, indent=2)  # 日本語含む可能性もあるので推奨 [web:755]

def load_best_params(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
