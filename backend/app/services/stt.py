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


import tempfile
from pathlib import Path


class WhisperSttService:
    """SttService backed by openai-whisper. Lazy-loads model on first call."""

    def __init__(self, model_name: str = "small", language: str = "vi") -> None:
        self._model_name = model_name
        self._language = language

    def _run_whisper(self, audio_path: str) -> dict:
        """Call into Whisper. Isolated for monkey-patching."""
        from app.services._model_cache import get_whisper
        model = get_whisper(self._model_name)
        return model.transcribe(audio_path, language=self._language, fp16=False)

    def transcribe(self, audio_bytes: bytes) -> SttResult:
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name
        try:
            raw = self._run_whisper(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
        return SttResult(
            transcript=raw["text"].strip(),
            language=raw.get("language", self._language),
        )
