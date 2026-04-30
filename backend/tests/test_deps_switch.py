from app.services.ocr import StubOcrService, PaddleOcrService, EasyOcrService
from app.services.stt import StubSttService, WhisperSttService


def test_get_ocr_service_returns_stub_by_default(monkeypatch):
    monkeypatch.setenv("VOICEAPP_USE_REAL_SERVICES", "0")
    import importlib
    from app.api import deps
    importlib.reload(deps)
    svc = deps.get_ocr_service()
    assert isinstance(svc, StubOcrService)


def test_get_ocr_service_returns_easyocr_by_default_when_real_enabled(monkeypatch):
    monkeypatch.setenv("VOICEAPP_USE_REAL_SERVICES", "1")
    monkeypatch.delenv("VOICEAPP_OCR_BACKEND", raising=False)
    import importlib
    from app.api import deps
    importlib.reload(deps)
    svc = deps.get_ocr_service()
    assert isinstance(svc, EasyOcrService)


def test_get_ocr_service_returns_paddle_when_backend_set(monkeypatch):
    monkeypatch.setenv("VOICEAPP_USE_REAL_SERVICES", "1")
    monkeypatch.setenv("VOICEAPP_OCR_BACKEND", "paddle")
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
