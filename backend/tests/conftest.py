import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.db import Base


@pytest.fixture
def engine(tmp_path):
    db = tmp_path / "test.db"
    eng = create_engine(f"sqlite:///{db}", connect_args={"check_same_thread": False})

    @event.listens_for(eng, "connect")
    def _on_connect(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    from app import models  # noqa: F401  (populate metadata)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db_session(engine):
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    with SessionLocal() as s:
        yield s


@pytest.fixture
def client(engine, db_session):
    """TestClient with DB and stub services injected."""
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.api.deps import get_db, get_ocr_service, get_stt_service
    from app.services.ocr import StubOcrService
    from app.services.stt import StubSttService

    app = create_app()

    def _get_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_ocr_service] = lambda: StubOcrService()
    app.dependency_overrides[get_stt_service] = lambda: StubSttService()

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
