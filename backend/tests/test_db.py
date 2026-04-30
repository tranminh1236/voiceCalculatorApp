from pathlib import Path
from sqlalchemy import text
from app.config import Settings
from app.db import make_engine, make_session_factory


def test_settings_defaults():
    s = Settings()
    assert s.db_path.endswith("voiceapp.db")
    assert s.media_dir.endswith("media")
    assert s.use_real_services is False
    assert s.whisper_model_name == "small"
    assert s.whisper_language == "vi"
    assert s.paddle_lang == "vi"


def test_engine_creates_sqlite_file(tmp_path: Path):
    db_file = tmp_path / "test.db"
    engine = make_engine(f"sqlite:///{db_file}")
    with engine.connect() as conn:
        conn.exec_driver_sql("SELECT 1")
    assert db_file.exists()


def test_session_factory_yields_sessions(tmp_path: Path):
    db_file = tmp_path / "test.db"
    engine = make_engine(f"sqlite:///{db_file}")
    SessionLocal = make_session_factory(engine)
    with SessionLocal() as s:
        result = s.execute(text("SELECT 1")).scalar()
    assert result == 1
