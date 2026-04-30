from collections.abc import Generator
from sqlalchemy.orm import Session
from app.db import make_engine, make_session_factory
from app.config import settings, Settings
from app.services.ocr import OcrService, StubOcrService, PaddleOcrService, EasyOcrService
from app.services.stt import SttService, StubSttService, WhisperSttService


_engine = make_engine(settings.db_url)
_SessionLocal = make_session_factory(_engine)


def get_db() -> Generator[Session, None, None]:
    with _SessionLocal() as s:
        yield s


def get_ocr_service() -> OcrService:
    _settings = Settings()
    if not _settings.use_real_services:
        return StubOcrService()
    if _settings.ocr_backend == "paddle":
        return PaddleOcrService(lang=_settings.paddle_lang)
    return EasyOcrService(lang=_settings.paddle_lang)


def get_stt_service() -> SttService:
    _settings = Settings()
    if _settings.use_real_services:
        return WhisperSttService(
            model_name=_settings.whisper_model_name,
            language=_settings.whisper_language,
        )
    return StubSttService()


def get_engine():
    return _engine
