from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SttResult:
    transcript: str
    language: str = "vi"


class SttService(Protocol):
    def transcribe(self, audio_bytes: bytes) -> SttResult: ...


class StubSttService:
    """Returns a fixed transcript — used until Plan 2 wires Whisper."""

    def transcribe(self, audio_bytes: bytes) -> SttResult:
        return SttResult(transcript="hai mươi ba cộng năm cộng một trăm lẻ năm bằng")
