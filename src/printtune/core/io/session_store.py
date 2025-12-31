# src/printtune/core/io/session_store.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..log_types import SessionRecord, RoundRecord, Candidate

def save_session(path: Path, session: SessionRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(session, f, ensure_ascii=False, indent=2, default=lambda o: o.__dict__)

def load_session(path: Path) -> SessionRecord:
    with path.open("r", encoding="utf-8") as f:
        d = json.load(f)

    rounds: list[RoundRecord] = []
    for rr in d["rounds"]:
        cands = [Candidate(**c) for c in rr["candidates"]]
        rounds.append(RoundRecord(
            round_id=rr["round_id"],
            round_index=int(rr["round_index"]),
            created_at=rr["created_at"],
            candidates=cands,
            judgment=rr.get("judgment"),
        ))

    return SessionRecord(
        session_id=d["session_id"],
        created_at=d["created_at"],
        sample_image_relpath=d["sample_image_relpath"],
        rounds=rounds,
        comparisons_global=d.get("comparisons_global", []),
    )
