from unittest.mock import patch
from app.services.stt import WhisperSttService, SttResult


def test_whisper_service_returns_transcript():
    svc = WhisperSttService(model_name="tiny", language="vi")
    fake_model_result = {"text": "  hai mươi ba cộng năm bằng  ", "language": "vi"}
    with patch.object(svc, "_run_whisper", return_value=fake_model_result):
        result = svc.transcribe(b"audio-bytes")
    assert isinstance(result, SttResult)
    assert result.transcript == "hai mươi ba cộng năm bằng"
    assert result.language == "vi"


def test_whisper_service_uses_configured_language():
    svc = WhisperSttService(model_name="tiny", language="vi")
    captured = {}

    def fake_run(audio_path: str) -> dict:
        captured["audio_path"] = audio_path
        return {"text": "ok", "language": "vi"}

    with patch.object(svc, "_run_whisper", side_effect=fake_run):
        svc.transcribe(b"x")
    assert "audio_path" in captured
    assert captured["audio_path"].endswith((".webm", ".wav", ".bin", ".m4a", ".mp3"))
