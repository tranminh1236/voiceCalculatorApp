import pytest
from app.services.audio import transcribe_and_parse
from app.services.stt import StubSttService, SttResult


class _FakeStt:
    def __init__(self, transcript: str) -> None:
        self._t = transcript

    def transcribe(self, audio_bytes: bytes) -> SttResult:
        return SttResult(transcript=self._t, language="vi")


def test_transcribe_and_parse_basic():
    stt = _FakeStt("hai mươi ba cộng năm cộng mười hai bằng")
    result = transcribe_and_parse(b"audio-bytes", stt)
    assert result.transcript == "hai mươi ba cộng năm cộng mười hai bằng"
    assert result.parsed_numbers == [23, 5, 12]
    assert result.sum == 40


def test_transcribe_and_parse_default_stub():
    """The default stub returns a fixed transcript ending with 'bằng'."""
    result = transcribe_and_parse(b"x", StubSttService())
    assert result.parsed_numbers == [23, 5, 105]
    assert result.sum == 133


def test_transcribe_and_parse_no_numbers_raises():
    stt = _FakeStt("xin chào bạn")
    with pytest.raises(ValueError):
        transcribe_and_parse(b"x", stt)
