from collections.abc import Generator
from sqlalchemy.orm import Session
from app.db import make_engine, make_session_factory
from app.config import settings
from app.services.ocr import OcrService, StubOcrService
from app.services.stt import SttService, StubSttService


_engine = make_engine(settings.db_url)
_SessionLocal = make_session_factory(_engine)


def get_db() -> Generator[Session, None, None]:
    with _SessionLocal() as s:
        yield s


def get_ocr_service() -> OcrService:
    return StubOcrService()


def get_stt_service() -> SttService:
    return StubSttService()


def get_engine():
    return _engine
