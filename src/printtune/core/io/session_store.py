# src/printtune/core/io/session_store.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..log_types import SessionRecord, RoundRecord, Candidate

def save_session(path: Path, session: SessionRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        # default=lambda o: o.__dict__ は dataclass のネストに対応しきれない場合があるので
        # asdict を使うか、慎重に行うのが良いが、現状で保存はできている前提とします。
        # dataclasses.asdict を使うのが一番安全です。
        import dataclasses
        json.dump(dataclasses.asdict(session), f, ensure_ascii=False, indent=2)

def load_session(path: Path) -> SessionRecord:
    with path.open("r", encoding="utf-8") as f:
        d = json.load(f)

    rounds: list[RoundRecord] = []
    for rr in d["rounds"]:
        # Candidateの復元
        cands = [Candidate(**c) for c in rr["candidates"]]
        
        # RoundRecordの復元
        # JSONに mode/purpose が保存されているはずなので、それを取得
        # キーがない場合のデフォルト値も念のため指定（過去データ互換）
        rounds.append(RoundRecord(
            round_id=rr["round_id"],
            round_index=int(rr["round_index"]),
            created_at=rr["created_at"],
            candidates=cands,
            judgment=rr.get("judgment"),
            mode=rr.get("mode", "pairwise"),      # ★ ここを追加
            purpose=rr.get("purpose", "unknown"), # ★ ここを追加
            delta_scale=float(rr.get("delta_scale", 1.0)), # ★ ここを追加
            meta=rr.get("meta", {}),              # ★ ここを追加
        ))

    return SessionRecord(
        session_id=d["session_id"],
        created_at=d["created_at"],
        sample_image_relpath=d["sample_image_relpath"],
        rounds=rounds,
        comparisons_global=d.get("comparisons_global", []),
    )
