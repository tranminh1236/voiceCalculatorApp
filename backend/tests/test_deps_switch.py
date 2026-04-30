from app.services.ocr import StubOcrService, PaddleOcrService
from app.services.stt import StubSttService, WhisperSttService


def test_get_ocr_service_returns_stub_by_default(monkeypatch):
    monkeypatch.setenv("VOICEAPP_USE_REAL_SERVICES", "0")
    import importlib
    from app.api import deps
    importlib.reload(deps)
    svc = deps.get_ocr_service()
    assert isinstance(svc, StubOcrService)


def test_get_ocr_service_returns_paddle_when_enabled(monkeypatch):
    monkeypatch.setenv("VOICEAPP_USE_REAL_SERVICES", "1")
    import importlib
    from app.api import deps
    importlib.reload(deps)
    svc = deps.get_ocr_service()
    assert isinstance(svc, PaddleOcrService)


def test_get_stt_service_returns_stub_by_default(monkeypatch):
    monkeypatch.setenv("VOICEAPP_USE_REAL_SERVICES", "0")
    import importlib
    from app.api import deps
    importlib.reload(deps)
    svc = deps.get_stt_service()
    assert isinstance(svc, StubSttService)


def test_get_stt_service_returns_whisper_when_enabled(monkeypatch):
    monkeypatch.setenv("VOICEAPP_USE_REAL_SERVICES", "1")
    import importlib
    from app.api import deps
    importlib.reload(deps)
    svc = deps.get_stt_service()
    assert isinstance(svc, WhisperSttService)
