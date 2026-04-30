"""Audio → numbers pipeline.

Pure function: takes raw audio bytes + an SttService, returns transcript + parsed numbers + sum.
No FastAPI, no DB — those concerns live in the API layer.
"""
from __future__ import annotations
from dataclasses import dataclass
from app.services.stt import SttService
from app.services.parser_vn import parse_expression


@dataclass(frozen=True)
class AudioPipelineResult:
    transcript: str
    language: str
    parsed_numbers: list[float]
    sum: float


def transcribe_and_parse(audio_bytes: bytes, stt: SttService) -> AudioPipelineResult:
    """Run STT then parse the resulting Vietnamese expression. Raises ValueError on bad input."""
    stt_result = stt.transcribe(audio_bytes)
    numbers, total = parse_expression(stt_result.transcript)
    return AudioPipelineResult(
        transcript=stt_result.transcript,
        language=stt_result.language,
        parsed_numbers=numbers,
        sum=total,
    )
