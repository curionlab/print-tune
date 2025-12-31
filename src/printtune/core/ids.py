# src/printtune/core/ids.py
from __future__ import annotations

from dataclasses import dataclass
import uuid

def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

@dataclass(frozen=True)
class SessionId:
    value: str

    @staticmethod
    def new() -> "SessionId":
        return SessionId(_new_id("sess"))

@dataclass(frozen=True)
class RoundId:
    value: str

    @staticmethod
    def new(session_id: SessionId, round_index: int) -> "RoundId":
        # round_indexは1始まり
        return RoundId(f"{session_id.value}_r{round_index:02d}_{uuid.uuid4().hex[:6]}")

@dataclass(frozen=True)
class CandidateId:
    value: str

    @staticmethod
    def new(round_id: RoundId, slot: str) -> "CandidateId":
        # slot: "A"/"B"/"C"/"D" 等（UI表示用の安定ラベル）
        return CandidateId(f"{round_id.value}_{slot}_{uuid.uuid4().hex[:6]}")

@dataclass(frozen=True)
class ArtifactId:
    value: str

    @staticmethod
    def new(session_id: SessionId, name: str) -> "ArtifactId":
        safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in name)
        return ArtifactId(f"{session_id.value}_{safe}_{uuid.uuid4().hex[:6]}")
