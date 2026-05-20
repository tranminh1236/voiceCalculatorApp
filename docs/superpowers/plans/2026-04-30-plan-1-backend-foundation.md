# Plan 1 — Backend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dựng Python backend (FastAPI + SQLite + SQLAlchemy) với toàn bộ data model, Vietnamese number parser hoàn chỉnh có test, stub OCR/STT services, và REST API CRUD cho templates + captures (chưa wire OCR/STT thật — để Plan 2). Cuối plan: chạy `pytest` xanh + curl được API.

**Architecture:** Modular Python package `app/`, tách services/api/models/schemas. SQLite file-based, no migrations tool (dùng `Base.metadata.create_all` cho personal scale). Test-driven cho parser (component có nhiều branch nhất). Dependency injection FastAPI để mock services trong test.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest, uvicorn. Quản lý deps bằng `requirements.txt` + venv (đơn giản hơn poetry cho personal use).

**Spec reference:** [docs/superpowers/specs/2026-04-30-voiceapp-handwritten-number-recognition-design.md](../specs/2026-04-30-voiceapp-handwritten-number-recognition-design.md)

---

## File Structure

```
voiceApp/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI entry, lifespan, CORS, DB init
│   │   ├── config.py                  # Settings (DB path, media dir, etc.)
│   │   ├── db.py                      # SQLAlchemy engine + session factory
│   │   ├── models.py                  # All ORM models in 1 file (8 tables)
│   │   ├── schemas.py                 # Pydantic schemas (request/response)
│   │   ├── seed.py                    # Province seed data
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py                # get_db, get_ocr_service, get_stt_service
│   │   │   ├── provinces.py           # GET /api/provinces
│   │   │   ├── templates.py           # CRUD /api/templates
│   │   │   └── captures.py            # POST/GET /api/captures (stub OCR)
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── ocr.py                 # Protocol + StubOcrService
│   │   │   ├── stt.py                 # Protocol + StubSttService
│   │   │   └── parser_vn.py           # Vietnamese number parser
│   │   └── domain/
│   │       ├── __init__.py
│   │       └── enums.py               # BetType, CaptureStatus, Region
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py                # pytest fixtures (test_db, client)
│   │   ├── test_parser_vn.py          # ~40 cases for VN parser
│   │   ├── test_models.py             # FK/constraint smoke tests
│   │   ├── test_api_provinces.py
│   │   ├── test_api_templates.py
│   │   └── test_api_captures.py
│   ├── data/                          # gitignored: voiceapp.db, media/
│   │   └── .gitkeep
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── pytest.ini
│   ├── .gitignore
│   └── README.md
└── .gitignore
```

**File responsibilities:**
- `models.py` — single source of truth cho schema; mọi bảng định nghĩa ở đây.
- `schemas.py` — Pydantic input/output, NEVER reuse ORM models trong API response.
- `services/parser_vn.py` — pure function, không phụ thuộc DB hay FastAPI; testable độc lập.
- `services/ocr.py` & `services/stt.py` — Protocol interface + Stub impl. Plan 2 sẽ thêm Real impl.
- `api/deps.py` — dependency providers; test override bằng `app.dependency_overrides`.
- `api/captures.py` — POST `/captures` gọi `ocr_service.extract(image)` (stub trả 3 fake numbers).

---

## Task 1: Repository scaffold & gitignore

**Files:**
- Create: `.gitignore`
- Create: `backend/.gitignore`
- Create: `backend/data/.gitkeep`
- Create: `backend/README.md`

- [ ] **Step 1: Create root `.gitignore`**

Create `/Users/it/Documents/MySource/voiceApp/.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
.venv/
env/
.env
*.egg-info/
.pytest_cache/
.coverage
htmlcov/

# IDEs
.vscode/
.idea/
*.swp
*.swo
.DS_Store

# Node (frontend - later plans)
node_modules/
dist/
build/
```

- [ ] **Step 2: Create `backend/.gitignore`**

Create `/Users/it/Documents/MySource/voiceApp/backend/.gitignore`:

```gitignore
data/voiceapp.db
data/voiceapp.db-journal
data/media/
*.log
```

- [ ] **Step 3: Create empty `backend/data/.gitkeep`**

Create `/Users/it/Documents/MySource/voiceApp/backend/data/.gitkeep` (empty file).

- [ ] **Step 4: Create `backend/README.md`**

Create `/Users/it/Documents/MySource/voiceApp/backend/README.md`:

````markdown
# VoiceApp Backend

FastAPI backend cho VoiceApp — Handwritten Number Recognition with Audio Supervision.

## Setup

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

## Test

```bash
pytest -v
```
````

- [ ] **Step 5: Init git + first commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git init
git add .gitignore backend/.gitignore backend/data/.gitkeep backend/README.md
git commit -m "chore: scaffold repo + backend skeleton"
```

Expected: 1 commit with 4 files.

---

## Task 2: Python project deps & venv

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/requirements-dev.txt`
- Create: `backend/pytest.ini`

- [ ] **Step 1: Create `requirements.txt`**

Create `/Users/it/Documents/MySource/voiceApp/backend/requirements.txt`:

```
fastapi==0.115.0
uvicorn[standard]==0.32.0
sqlalchemy==2.0.36
pydantic==2.9.2
pydantic-settings==2.6.0
python-multipart==0.0.12
```

- [ ] **Step 2: Create `requirements-dev.txt`**

Create `/Users/it/Documents/MySource/voiceApp/backend/requirements-dev.txt`:

```
pytest==8.3.3
pytest-asyncio==0.24.0
httpx==0.27.2
ruff==0.7.1
```

- [ ] **Step 3: Create `pytest.ini`**

Create `/Users/it/Documents/MySource/voiceApp/backend/pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
asyncio_mode = auto
```

- [ ] **Step 4: Create venv + install deps**

```bash
cd /Users/it/Documents/MySource/voiceApp/backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Expected: tất cả install thành công, không error.

- [ ] **Step 5: Verify pytest runs (no tests yet)**

```bash
cd /Users/it/Documents/MySource/voiceApp/backend
source .venv/bin/activate
pytest
```

Expected: `no tests ran` (exit code 5 — chấp nhận được, chỉ verify pytest install).

- [ ] **Step 6: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/requirements.txt backend/requirements-dev.txt backend/pytest.ini
git commit -m "chore(backend): add python deps + pytest config"
```

---

## Task 3: Domain enums

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/domain/__init__.py`
- Create: `backend/app/domain/enums.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_enums.py`

- [ ] **Step 1: Create empty `__init__.py` files**

Create:
- `/Users/it/Documents/MySource/voiceApp/backend/app/__init__.py` (empty)
- `/Users/it/Documents/MySource/voiceApp/backend/app/domain/__init__.py` (empty)
- `/Users/it/Documents/MySource/voiceApp/backend/tests/__init__.py` (empty)

- [ ] **Step 2: Write failing test for enums**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_enums.py`:

```python
from app.domain.enums import BetType, CaptureStatus, Region, MatchSource


def test_bet_type_members():
    assert BetType.LO.value == "lo"
    assert BetType.DE.value == "de"
    assert BetType.XIEN_2.value == "xien_2"
    assert BetType.XIEN_3.value == "xien_3"
    assert BetType.XIEN_4.value == "xien_4"
    assert BetType.BA_CANG.value == "3cang"
    assert BetType.XIEN_QUAY.value == "xien_quay"


def test_capture_status_members():
    assert CaptureStatus.DRAFT.value == "draft"
    assert CaptureStatus.FINAL.value == "final"
    assert CaptureStatus.SETTLED.value == "settled"


def test_region_members():
    assert Region.MB.value == "mb"
    assert Region.MT.value == "mt"
    assert Region.MN.value == "mn"


def test_match_source_members():
    assert MatchSource.AUTO.value == "auto"
    assert MatchSource.MANUAL.value == "manual"
```

- [ ] **Step 3: Run test — expect FAIL**

```bash
cd /Users/it/Documents/MySource/voiceApp/backend
source .venv/bin/activate
pytest tests/test_enums.py -v
```

Expected: FAIL với `ModuleNotFoundError: No module named 'app.domain.enums'`.

- [ ] **Step 4: Implement `enums.py`**

Create `/Users/it/Documents/MySource/voiceApp/backend/app/domain/enums.py`:

```python
from enum import Enum


class BetType(str, Enum):
    LO = "lo"
    DE = "de"
    XIEN_2 = "xien_2"
    XIEN_3 = "xien_3"
    XIEN_4 = "xien_4"
    BA_CANG = "3cang"
    XIEN_QUAY = "xien_quay"


class CaptureStatus(str, Enum):
    DRAFT = "draft"
    FINAL = "final"
    SETTLED = "settled"


class Region(str, Enum):
    MB = "mb"
    MT = "mt"
    MN = "mn"


class MatchSource(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"
```

- [ ] **Step 5: Run test — expect PASS**

```bash
pytest tests/test_enums.py -v
```

Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/__init__.py backend/app/domain/__init__.py backend/app/domain/enums.py backend/tests/__init__.py backend/tests/test_enums.py
git commit -m "feat(backend): add domain enums (BetType, CaptureStatus, Region, MatchSource)"
```

---

## Task 4: Config & DB engine

**Files:**
- Create: `backend/app/config.py`
- Create: `backend/app/db.py`
- Create: `backend/tests/test_db.py`

- [ ] **Step 1: Write failing test for config**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_db.py`:

```python
from pathlib import Path
from app.config import Settings
from app.db import make_engine, make_session_factory


def test_settings_defaults():
    s = Settings()
    assert s.db_path.endswith("voiceapp.db")
    assert s.media_dir.endswith("media")


def test_engine_creates_sqlite_file(tmp_path: Path):
    db_file = tmp_path / "test.db"
    engine = make_engine(f"sqlite:///{db_file}")
    # connect to force sqlite to create the file
    with engine.connect() as conn:
        conn.exec_driver_sql("SELECT 1")
    assert db_file.exists()


def test_session_factory_yields_sessions(tmp_path: Path):
    db_file = tmp_path / "test.db"
    engine = make_engine(f"sqlite:///{db_file}")
    SessionLocal = make_session_factory(engine)
    with SessionLocal() as s:
        result = s.execute_driver_sql := None  # placeholder; just ensure context works
    assert SessionLocal is not None
```

Note: 3rd test trên là smoke check; điều quan trọng là `SessionLocal()` context manager mở/đóng được không lỗi.

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tests/test_db.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.config'`.

- [ ] **Step 3: Implement `config.py`**

Create `/Users/it/Documents/MySource/voiceApp/backend/app/config.py`:

```python
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parent.parent  # backend/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VOICEAPP_", env_file=".env", extra="ignore")

    db_path: str = str(BACKEND_ROOT / "data" / "voiceapp.db")
    media_dir: str = str(BACKEND_ROOT / "data" / "media")
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @property
    def db_url(self) -> str:
        return f"sqlite:///{self.db_path}"


settings = Settings()
```

- [ ] **Step 4: Implement `db.py`**

Create `/Users/it/Documents/MySource/voiceApp/backend/app/db.py`:

```python
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def make_engine(url: str) -> Engine:
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
        future=True,
    )

    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _enable_fk(dbapi_conn, _):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

    return engine


def make_session_factory(engine: Engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
```

- [ ] **Step 5: Fix the test (3rd one is malformed)**

Edit `/Users/it/Documents/MySource/voiceApp/backend/tests/test_db.py`, replace the 3rd test entirely:

```python
def test_session_factory_yields_sessions(tmp_path: Path):
    db_file = tmp_path / "test.db"
    engine = make_engine(f"sqlite:///{db_file}")
    SessionLocal = make_session_factory(engine)
    with SessionLocal() as s:
        from sqlalchemy import text
        result = s.execute(text("SELECT 1")).scalar()
    assert result == 1
```

- [ ] **Step 6: Run test — expect PASS**

```bash
pytest tests/test_db.py -v
```

Expected: 3 passed.

- [ ] **Step 7: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/config.py backend/app/db.py backend/tests/test_db.py
git commit -m "feat(backend): add Settings + SQLAlchemy engine factory with FK enforced"
```

---

## Task 5: ORM models — Provinces + Templates

**Files:**
- Create: `backend/app/models.py`
- Modify (later): `backend/app/models.py` (add more models in subsequent tasks)
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_models_provinces_templates.py`

- [ ] **Step 1: Create `conftest.py` với fixture `db_session`**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/conftest.py`:

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base


@pytest.fixture
def engine(tmp_path):
    db = tmp_path / "test.db"
    eng = create_engine(f"sqlite:///{db}", connect_args={"check_same_thread": False})
    # enable FK for sqlite
    from sqlalchemy import event
    @event.listens_for(eng, "connect")
    def _on_connect(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()
    # import models so metadata is populated
    from app import models  # noqa: F401
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db_session(engine):
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    with SessionLocal() as s:
        yield s
```

- [ ] **Step 2: Write failing test for Province + Template models**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_models_provinces_templates.py`:

```python
import json
from app.models import Province, Template


def test_create_province(db_session):
    p = Province(code="HN", region="mb", name="Hà Nội")
    db_session.add(p)
    db_session.commit()
    fetched = db_session.get(Province, "HN")
    assert fetched.name == "Hà Nội"
    assert fetched.region == "mb"


def test_create_template_with_groups(db_session):
    groups = [
        {"index": 1, "label": "Lô", "bet_type": "lo", "multiplier": 80.0},
        {"index": 2, "label": "Đề", "bet_type": "de", "multiplier": 82.0},
        {"index": 3, "label": "Xiên 2", "bet_type": "xien_2", "multiplier": 14.5},
    ]
    t = Template(name="Lô-Đề-Xiên", groups_json=json.dumps(groups))
    db_session.add(t)
    db_session.commit()
    assert t.id is not None
    loaded_groups = json.loads(t.groups_json)
    assert len(loaded_groups) == 3
    assert loaded_groups[1]["bet_type"] == "de"
```

- [ ] **Step 3: Run test — expect FAIL**

```bash
pytest tests/test_models_provinces_templates.py -v
```

Expected: FAIL — `cannot import name 'Province' from 'app.models'`.

- [ ] **Step 4: Implement Province + Template in `models.py`**

Create `/Users/it/Documents/MySource/voiceApp/backend/app/models.py`:

```python
from datetime import datetime, timezone
from sqlalchemy import (
    CheckConstraint, ForeignKey, Integer, Float, String, Text, UniqueConstraint, DateTime
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Province(Base):
    __tablename__ = "provinces"
    code: Mapped[str] = mapped_column(String(8), primary_key=True)
    region: Mapped[str] = mapped_column(String(2), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    __table_args__ = (
        CheckConstraint("region IN ('mb','mt','mn')", name="ck_province_region"),
    )


class Template(Base):
    __tablename__ = "templates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    groups_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON list[GroupDef]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
```

- [ ] **Step 5: Run test — expect PASS**

```bash
pytest tests/test_models_provinces_templates.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/models.py backend/tests/conftest.py backend/tests/test_models_provinces_templates.py
git commit -m "feat(backend): add Province and Template ORM models"
```

---

## Task 6: ORM models — Capture + OcrNumber + AudioGroup + Match

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/tests/test_models_capture.py`

- [ ] **Step 1: Write failing tests**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_models_capture.py`:

```python
import json
import pytest
from sqlalchemy.exc import IntegrityError
from app.models import Template, Capture, OcrNumber, AudioGroup, Match


def _mk_template(db_session) -> Template:
    t = Template(name="T1", groups_json=json.dumps([
        {"index": 1, "label": "G1", "bet_type": "lo", "multiplier": 80.0},
    ]))
    db_session.add(t)
    db_session.commit()
    return t


def test_create_capture(db_session):
    t = _mk_template(db_session)
    c = Capture(
        template_id=t.id,
        image_path="/tmp/x.jpg",
        status="draft",
        group_provinces_json=json.dumps({"1": ["HN"]}),
    )
    db_session.add(c)
    db_session.commit()
    assert c.id is not None
    assert c.status == "draft"


def test_capture_invalid_status_raises(db_session):
    t = _mk_template(db_session)
    c = Capture(
        template_id=t.id,
        image_path="/tmp/x.jpg",
        status="bogus",
        group_provinces_json=json.dumps({"1": ["HN"]}),
    )
    db_session.add(c)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_ocr_number_cascade_delete(db_session):
    t = _mk_template(db_session)
    c = Capture(template_id=t.id, image_path="/tmp/x.jpg", status="draft",
                group_provinces_json=json.dumps({"1": ["HN"]}))
    db_session.add(c); db_session.commit()
    n = OcrNumber(capture_id=c.id, bbox_x=0, bbox_y=0, bbox_w=10, bbox_h=10, raw_text="23", raw_value=23.0, confidence=0.9)
    db_session.add(n); db_session.commit()
    db_session.delete(c); db_session.commit()
    assert db_session.query(OcrNumber).count() == 0


def test_match_allows_duplicate_pair(db_session):
    """Same OCR can match same audio_group multiple times (rule: 2a + 2c)."""
    t = _mk_template(db_session)
    c = Capture(template_id=t.id, image_path="/tmp/x.jpg", status="draft",
                group_provinces_json=json.dumps({"1": ["HN"]}))
    db_session.add(c); db_session.commit()
    n = OcrNumber(capture_id=c.id, bbox_x=0, bbox_y=0, bbox_w=10, bbox_h=10, raw_text="23", raw_value=23.0, confidence=0.9)
    g = AudioGroup(capture_id=c.id, group_index=1, audio_path="/tmp/a.webm", multiplier_snapshot=80.0)
    db_session.add_all([n, g]); db_session.commit()
    m1 = Match(ocr_number_id=n.id, audio_group_id=g.id, confidence=1.0, source="auto")
    m2 = Match(ocr_number_id=n.id, audio_group_id=g.id, confidence=1.0, source="auto")
    db_session.add_all([m1, m2]); db_session.commit()
    assert db_session.query(Match).count() == 2
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/test_models_capture.py -v
```

Expected: FAIL — Capture/OcrNumber/AudioGroup/Match not found.

- [ ] **Step 3: Append models to `models.py`**

Append to `/Users/it/Documents/MySource/voiceApp/backend/app/models.py`:

```python
class Capture(Base):
    __tablename__ = "captures"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id"), nullable=False)
    image_path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    final_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    group_provinces_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON dict {group_index_str: [province_codes]}
    writer_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    note_date: Mapped[str | None] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD
    tags_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)
    __table_args__ = (
        CheckConstraint("status IN ('draft','final','settled')", name="ck_capture_status"),
    )


class OcrNumber(Base):
    __tablename__ = "ocr_numbers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    capture_id: Mapped[int] = mapped_column(ForeignKey("captures.id", ondelete="CASCADE"), nullable=False)
    bbox_x: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_y: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_w: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_h: Mapped[float] = mapped_column(Float, nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    corrected_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)


class AudioGroup(Base):
    __tablename__ = "audio_groups"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    capture_id: Mapped[int] = mapped_column(ForeignKey("captures.id", ondelete="CASCADE"), nullable=False)
    group_index: Mapped[int] = mapped_column(Integer, nullable=False)
    audio_path: Mapped[str] = mapped_column(Text, nullable=False)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_numbers_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    sum: Mapped[float | None] = mapped_column(Float, nullable=True)
    multiplier_snapshot: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)


class Match(Base):
    __tablename__ = "matches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ocr_number_id: Mapped[int] = mapped_column(ForeignKey("ocr_numbers.id", ondelete="CASCADE"), nullable=False)
    audio_group_id: Mapped[int] = mapped_column(ForeignKey("audio_groups.id", ondelete="CASCADE"), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(8), nullable=False)
    __table_args__ = (
        CheckConstraint("source IN ('auto','manual')", name="ck_match_source"),
    )
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_models_capture.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/models.py backend/tests/test_models_capture.py
git commit -m "feat(backend): add Capture, OcrNumber, AudioGroup, Match models"
```

---

## Task 7: ORM models — LotteryDraw + CaptureResult

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/tests/test_models_lottery.py`

- [ ] **Step 1: Write failing tests**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_models_lottery.py`:

```python
import json
import pytest
from sqlalchemy.exc import IntegrityError
from app.models import Province, Template, Capture, LotteryDraw, CaptureResult


def _setup_basic(db_session):
    p = Province(code="HN", region="mb", name="Hà Nội")
    t = Template(name="T", groups_json=json.dumps([{"index": 1, "label": "G", "bet_type": "lo", "multiplier": 80.0}]))
    db_session.add_all([p, t]); db_session.commit()
    return p, t


def test_create_lottery_draw(db_session):
    p, _ = _setup_basic(db_session)
    d = LotteryDraw(
        province_code="HN",
        draw_date="2026-04-29",
        prizes_json=json.dumps({"DB": ["86569"]}),
        tails_2d_json=json.dumps([69, 20, 44]),
        special_tail_2d=69,
    )
    db_session.add(d); db_session.commit()
    assert d.id is not None


def test_lottery_draw_unique_province_date(db_session):
    p, _ = _setup_basic(db_session)
    d1 = LotteryDraw(province_code="HN", draw_date="2026-04-29",
                     prizes_json="{}", tails_2d_json="[]", special_tail_2d=0)
    d2 = LotteryDraw(province_code="HN", draw_date="2026-04-29",
                     prizes_json="{}", tails_2d_json="[]", special_tail_2d=0)
    db_session.add(d1); db_session.commit()
    db_session.add(d2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_capture_result_unique_per_capture(db_session):
    p, t = _setup_basic(db_session)
    c = Capture(template_id=t.id, image_path="/x", status="final", group_provinces_json=json.dumps({"1": ["HN"]}))
    db_session.add(c); db_session.commit()
    r1 = CaptureResult(capture_id=c.id, hits_json="{}", total_stake=0, winning_total_payout=0, profit_loss=0,
                       settled_at=__import__('datetime').datetime.utcnow())
    db_session.add(r1); db_session.commit()
    r2 = CaptureResult(capture_id=c.id, hits_json="{}", total_stake=0, winning_total_payout=0, profit_loss=0,
                       settled_at=__import__('datetime').datetime.utcnow())
    db_session.add(r2)
    with pytest.raises(IntegrityError):
        db_session.commit()
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/test_models_lottery.py -v
```

Expected: FAIL — LotteryDraw/CaptureResult not found.

- [ ] **Step 3: Append to `models.py`**

Append to `/Users/it/Documents/MySource/voiceApp/backend/app/models.py`:

```python
class LotteryDraw(Base):
    __tablename__ = "lottery_draws"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    province_code: Mapped[str] = mapped_column(ForeignKey("provinces.code"), nullable=False)
    draw_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    source_image_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    prizes_json: Mapped[str] = mapped_column(Text, nullable=False)
    tails_2d_json: Mapped[str] = mapped_column(Text, nullable=False)
    special_tail_2d: Mapped[int] = mapped_column(Integer, nullable=False)
    __table_args__ = (
        UniqueConstraint("province_code", "draw_date", name="uq_lottery_province_date"),
    )


class CaptureResult(Base):
    __tablename__ = "capture_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    capture_id: Mapped[int] = mapped_column(ForeignKey("captures.id", ondelete="CASCADE"), nullable=False, unique=True)
    hits_json: Mapped[str] = mapped_column(Text, nullable=False)
    total_stake: Mapped[float] = mapped_column(Float, nullable=False)
    winning_total_payout: Mapped[float] = mapped_column(Float, nullable=False)
    profit_loss: Mapped[float] = mapped_column(Float, nullable=False)
    settled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_models_lottery.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Run all model tests**

```bash
pytest tests/test_models_provinces_templates.py tests/test_models_capture.py tests/test_models_lottery.py tests/test_enums.py tests/test_db.py -v
```

Expected: tất cả pass (12+ tests).

- [ ] **Step 6: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/models.py backend/tests/test_models_lottery.py
git commit -m "feat(backend): add LotteryDraw and CaptureResult models with unique constraints"
```

---

## Task 8: Province seed data

**Files:**
- Create: `backend/app/seed.py`
- Create: `backend/tests/test_seed.py`

- [ ] **Step 1: Write failing test**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_seed.py`:

```python
from app.models import Province
from app.seed import seed_provinces, PROVINCES


def test_provinces_constant_has_all_three_regions():
    regions = {p["region"] for p in PROVINCES}
    assert regions == {"mb", "mt", "mn"}


def test_provinces_has_required_codes():
    codes = {p["code"] for p in PROVINCES}
    # Must at least include these for spec examples
    assert {"HN", "DNG", "KH"}.issubset(codes)


def test_seed_inserts_all(db_session):
    seed_provinces(db_session)
    db_session.commit()
    n = db_session.query(Province).count()
    assert n == len(PROVINCES)


def test_seed_idempotent(db_session):
    seed_provinces(db_session)
    db_session.commit()
    seed_provinces(db_session)
    db_session.commit()
    n = db_session.query(Province).count()
    assert n == len(PROVINCES)
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/test_seed.py -v
```

Expected: FAIL — `cannot import name 'seed_provinces'`.

- [ ] **Step 3: Implement `seed.py`**

Create `/Users/it/Documents/MySource/voiceApp/backend/app/seed.py`:

```python
from sqlalchemy.orm import Session
from app.models import Province


PROVINCES: list[dict] = [
    # Miền Bắc (1 đài/ngày)
    {"code": "HN", "region": "mb", "name": "Hà Nội"},

    # Miền Trung
    {"code": "DNG", "region": "mt", "name": "Đà Nẵng"},
    {"code": "KH", "region": "mt", "name": "Khánh Hòa"},
    {"code": "TTH", "region": "mt", "name": "Thừa Thiên Huế"},
    {"code": "PY", "region": "mt", "name": "Phú Yên"},
    {"code": "DLK", "region": "mt", "name": "Đắk Lắk"},
    {"code": "QNM", "region": "mt", "name": "Quảng Nam"},
    {"code": "DNO", "region": "mt", "name": "Đắk Nông"},
    {"code": "NT", "region": "mt", "name": "Ninh Thuận"},
    {"code": "GL", "region": "mt", "name": "Gia Lai"},
    {"code": "QNG", "region": "mt", "name": "Quảng Ngãi"},
    {"code": "BD", "region": "mt", "name": "Bình Định"},
    {"code": "QT", "region": "mt", "name": "Quảng Trị"},
    {"code": "QB", "region": "mt", "name": "Quảng Bình"},
    {"code": "KT", "region": "mt", "name": "Kon Tum"},

    # Miền Nam
    {"code": "TPHCM", "region": "mn", "name": "TP. Hồ Chí Minh"},
    {"code": "DT", "region": "mn", "name": "Đồng Tháp"},
    {"code": "CM", "region": "mn", "name": "Cà Mau"},
    {"code": "BL", "region": "mn", "name": "Bạc Liêu"},
    {"code": "BTR", "region": "mn", "name": "Bến Tre"},
    {"code": "VT", "region": "mn", "name": "Vũng Tàu"},
    {"code": "BTH", "region": "mn", "name": "Bình Thuận"},
    {"code": "DN", "region": "mn", "name": "Đồng Nai"},
    {"code": "CT", "region": "mn", "name": "Cần Thơ"},
    {"code": "ST", "region": "mn", "name": "Sóc Trăng"},
    {"code": "TN", "region": "mn", "name": "Tây Ninh"},
    {"code": "AG", "region": "mn", "name": "An Giang"},
    {"code": "VL", "region": "mn", "name": "Vĩnh Long"},
    {"code": "BDU", "region": "mn", "name": "Bình Dương"},
    {"code": "TG", "region": "mn", "name": "Tiền Giang"},
    {"code": "KG", "region": "mn", "name": "Kiên Giang"},
    {"code": "LA", "region": "mn", "name": "Long An"},
    {"code": "HG", "region": "mn", "name": "Hậu Giang"},
    {"code": "BP", "region": "mn", "name": "Bình Phước"},
    {"code": "TV", "region": "mn", "name": "Trà Vinh"},
]


def seed_provinces(session: Session) -> int:
    """Insert provinces if not exist. Returns number inserted."""
    existing = {p.code for p in session.query(Province).all()}
    inserted = 0
    for entry in PROVINCES:
        if entry["code"] in existing:
            continue
        session.add(Province(**entry))
        inserted += 1
    return inserted
```

Note: list province trên là tối thiểu cho 3 miền — Plan sau có thể bổ sung khi cần.

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_seed.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/seed.py backend/tests/test_seed.py
git commit -m "feat(backend): add province seed data covering 3 regions"
```

---

## Task 9: Vietnamese number parser — units & teens

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/parser_vn.py`
- Create: `backend/tests/test_parser_vn.py`

The parser is implemented incrementally over Tasks 9-13. Each task adds capability + tests.

- [ ] **Step 1: Create `services/__init__.py`**

Create `/Users/it/Documents/MySource/voiceApp/backend/app/services/__init__.py` (empty).

- [ ] **Step 2: Write failing test for digits 0-9 + teens**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_parser_vn.py`:

```python
import pytest
from app.services.parser_vn import parse_number_word, parse_expression


@pytest.mark.parametrize("word,expected", [
    ("không", 0),
    ("một", 1),
    ("hai", 2),
    ("ba", 3),
    ("bốn", 4),
    ("năm", 5),
    ("sáu", 6),
    ("bảy", 7),
    ("tám", 8),
    ("chín", 9),
])
def test_parse_single_digits(word, expected):
    assert parse_number_word(word) == expected


@pytest.mark.parametrize("phrase,expected", [
    ("mười", 10),
    ("mười một", 11),
    ("mười hai", 12),
    ("mười lăm", 15),
    ("mười tám", 18),
])
def test_parse_teens(phrase, expected):
    assert parse_number_word(phrase) == expected
```

- [ ] **Step 3: Run — expect FAIL**

```bash
pytest tests/test_parser_vn.py -v
```

Expected: FAIL — module not found.

- [ ] **Step 4: Implement minimal parser for units + teens**

Create `/Users/it/Documents/MySource/voiceApp/backend/app/services/parser_vn.py`:

```python
"""Vietnamese number-word parser.

Supported (incrementally extended):
- Digits 0-9
- Teens (10-19): "mười", "mười X"
- Tens (20-99): "X mươi", "X mươi Y" — Task 10
- Hundreds (100-999): "X trăm", "X trăm lẻ Y", "X trăm Y mươi Z" — Task 11
- Thousands/millions/billions — Task 12
- Special words: "rưỡi", "phẩy", "âm", variants ("linh"/"lẻ", "tư"/"bốn", "lăm"/"năm", "mốt"/"một") — Task 12
- Expression parsing with delimiter "cộng" and terminator "bằng/=/tổng" — Task 13
"""
from __future__ import annotations


_DIGITS: dict[str, int] = {
    "không": 0, "một": 1, "hai": 2, "ba": 3, "bốn": 4,
    "năm": 5, "sáu": 6, "bảy": 7, "tám": 8, "chín": 9,
}


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())


def parse_number_word(text: str) -> float:
    """Parse a Vietnamese number phrase (no operators) into a number.

    Raises ValueError if the input is unparseable.
    """
    text = _normalize(text)
    if not text:
        raise ValueError("empty input")
    tokens = text.split()
    return _parse_tokens(tokens)


def _parse_tokens(tokens: list[str]) -> float:
    if len(tokens) == 1:
        t = tokens[0]
        if t in _DIGITS:
            return _DIGITS[t]
        if t == "mười":
            return 10
        raise ValueError(f"unknown token: {t!r}")
    if len(tokens) == 2 and tokens[0] == "mười":
        # mười X → 10 + X (with "lăm" → 5)
        unit = tokens[1]
        if unit == "lăm":
            return 15
        if unit in _DIGITS:
            return 10 + _DIGITS[unit]
        raise ValueError(f"unknown unit after 'mười': {unit!r}")
    raise ValueError(f"cannot parse: {tokens!r}")


def parse_expression(text: str) -> tuple[list[float], float]:
    """Parse 'X cộng Y cộng Z bằng' → ([X, Y, Z], sum). Implemented in Task 13."""
    raise NotImplementedError
```

- [ ] **Step 5: Run — expect PASS**

```bash
pytest tests/test_parser_vn.py -v
```

Expected: 15 passed (10 digits + 5 teens).

- [ ] **Step 6: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/services/__init__.py backend/app/services/parser_vn.py backend/tests/test_parser_vn.py
git commit -m "feat(parser): support digits 0-9 and teens 10-19"
```

---

## Task 10: VN parser — tens (20-99)

**Files:**
- Modify: `backend/app/services/parser_vn.py`
- Modify: `backend/tests/test_parser_vn.py`

- [ ] **Step 1: Add failing tests for tens**

Append to `/Users/it/Documents/MySource/voiceApp/backend/tests/test_parser_vn.py`:

```python
@pytest.mark.parametrize("phrase,expected", [
    ("hai mươi", 20),
    ("hai mươi ba", 23),
    ("hai mươi tư", 24),       # variant: tư = 4
    ("hai mươi bốn", 24),
    ("hai mươi lăm", 25),
    ("hai mươi mốt", 21),      # variant: mốt = 1 (only after "mươi")
    ("ba mươi", 30),
    ("chín mươi chín", 99),
])
def test_parse_tens(phrase, expected):
    assert parse_number_word(phrase) == expected
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/test_parser_vn.py::test_parse_tens -v
```

Expected: FAIL on most cases.

- [ ] **Step 3: Extend parser**

Replace the body of `_parse_tokens` in `/Users/it/Documents/MySource/voiceApp/backend/app/services/parser_vn.py`:

```python
def _parse_tokens(tokens: list[str]) -> float:
    # Single token
    if len(tokens) == 1:
        t = tokens[0]
        if t in _DIGITS:
            return _DIGITS[t]
        if t == "mười":
            return 10
        raise ValueError(f"unknown token: {t!r}")

    # 2-token forms
    if len(tokens) == 2:
        a, b = tokens
        if a == "mười":
            # teen: mười X (lăm = 5)
            if b == "lăm":
                return 15
            if b in _DIGITS:
                return 10 + _DIGITS[b]
            raise ValueError(f"unknown unit after 'mười': {b!r}")
        if b == "mươi":
            # X mươi → X*10
            if a in _DIGITS and _DIGITS[a] >= 2:
                return _DIGITS[a] * 10
            raise ValueError(f"invalid tens prefix: {a!r}")

    # 3-token form: X mươi Y
    if len(tokens) == 3 and tokens[1] == "mươi":
        a, _, c = tokens
        if a not in _DIGITS or _DIGITS[a] < 2:
            raise ValueError(f"invalid tens prefix: {a!r}")
        tens = _DIGITS[a] * 10
        unit = _UNIT_AFTER_MUOI.get(c)
        if unit is None:
            raise ValueError(f"unknown unit after '{a} mươi': {c!r}")
        return tens + unit

    raise ValueError(f"cannot parse: {tokens!r}")
```

Add at module-level (above `parse_number_word`):

```python
_UNIT_AFTER_MUOI: dict[str, int] = {
    **_DIGITS,
    "tư": 4,
    "lăm": 5,
    "mốt": 1,
}
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_parser_vn.py -v
```

Expected: all previous + 8 new tens tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/services/parser_vn.py backend/tests/test_parser_vn.py
git commit -m "feat(parser): support tens 20-99 with variants tư/lăm/mốt"
```

---

## Task 11: VN parser — hundreds (100-999)

**Files:**
- Modify: `backend/app/services/parser_vn.py`
- Modify: `backend/tests/test_parser_vn.py`

- [ ] **Step 1: Add failing tests**

Append to `/Users/it/Documents/MySource/voiceApp/backend/tests/test_parser_vn.py`:

```python
@pytest.mark.parametrize("phrase,expected", [
    ("một trăm", 100),
    ("hai trăm", 200),
    ("một trăm lẻ năm", 105),
    ("một trăm linh năm", 105),       # variant linh = lẻ
    ("trăm lẻ năm", 105),             # ellided "một"
    ("một trăm hai mươi ba", 123),
    ("chín trăm chín mươi chín", 999),
    ("một trăm mười", 110),
    ("một trăm mười tám", 118),
])
def test_parse_hundreds(phrase, expected):
    assert parse_number_word(phrase) == expected
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/test_parser_vn.py -v -k hundreds
```

- [ ] **Step 3: Refactor to recursive composition + add hundreds**

Replace the entire body of `parser_vn.py` (everything below `_DIGITS` constant) with:

```python
_UNIT_AFTER_MUOI: dict[str, int] = {
    **_DIGITS,
    "tư": 4,
    "lăm": 5,
    "mốt": 1,
}

_LE = {"lẻ", "linh"}


def _parse_under_100(tokens: list[str]) -> int:
    """Parse 0-99 from tokens. Returns int, raises ValueError if not valid."""
    if not tokens:
        raise ValueError("empty under-100 token list")
    if len(tokens) == 1:
        t = tokens[0]
        if t in _DIGITS:
            return _DIGITS[t]
        if t == "mười":
            return 10
        raise ValueError(f"unknown 0-9 token: {t!r}")
    if len(tokens) == 2:
        a, b = tokens
        if a == "mười":
            if b == "lăm":
                return 15
            if b in _DIGITS:
                return 10 + _DIGITS[b]
            raise ValueError(f"bad teen unit: {b!r}")
        if b == "mươi":
            if a in _DIGITS and _DIGITS[a] >= 2:
                return _DIGITS[a] * 10
            raise ValueError(f"bad tens prefix: {a!r}")
    if len(tokens) == 3 and tokens[1] == "mươi":
        a, _, c = tokens
        if a not in _DIGITS or _DIGITS[a] < 2:
            raise ValueError(f"bad tens prefix: {a!r}")
        unit = _UNIT_AFTER_MUOI.get(c)
        if unit is None:
            raise ValueError(f"bad unit after '{a} mươi': {c!r}")
        return _DIGITS[a] * 10 + unit
    raise ValueError(f"under-100 cannot parse: {tokens!r}")


def _parse_under_1000(tokens: list[str]) -> int:
    """Parse 0-999 from tokens, treating 'trăm' as the 100-multiplier."""
    if "trăm" not in tokens:
        return _parse_under_100(tokens)

    idx = tokens.index("trăm")
    head, tail = tokens[:idx], tokens[idx + 1:]

    # head: hundreds digit (may be elided → assume 1)
    if not head:
        hundreds = 1
    elif len(head) == 1 and head[0] in _DIGITS:
        hundreds = _DIGITS[head[0]]
    else:
        raise ValueError(f"bad hundreds prefix: {head!r}")

    if not tail:
        return hundreds * 100

    # tail starts with 'lẻ'/'linh' OR is a normal under-100 phrase
    if tail[0] in _LE:
        rest = tail[1:]
        if len(rest) != 1 or rest[0] not in _DIGITS:
            raise ValueError(f"bad 'lẻ' tail: {tail!r}")
        return hundreds * 100 + _DIGITS[rest[0]]

    return hundreds * 100 + _parse_under_100(tail)


def parse_number_word(text: str) -> float:
    text = _normalize(text)
    if not text:
        raise ValueError("empty input")
    tokens = text.split()
    return _parse_under_1000(tokens)


def parse_expression(text: str) -> tuple[list[float], float]:
    raise NotImplementedError
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_parser_vn.py -v
```

Expected: all previous + 9 hundreds tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/services/parser_vn.py backend/tests/test_parser_vn.py
git commit -m "feat(parser): support hundreds 100-999 with lẻ/linh and elided một"
```

---

## Task 12: VN parser — thousands, millions, special words

**Files:**
- Modify: `backend/app/services/parser_vn.py`
- Modify: `backend/tests/test_parser_vn.py`

- [ ] **Step 1: Add failing tests**

Append to `/Users/it/Documents/MySource/voiceApp/backend/tests/test_parser_vn.py`:

```python
@pytest.mark.parametrize("phrase,expected", [
    ("một nghìn", 1000),
    ("một nghìn không trăm năm mươi", 1050),
    ("một nghìn không trăm lẻ năm", 1005),
    ("hai nghìn rưỡi", 2500),                 # rưỡi = +500 of next-lower unit
    ("ba trăm rưỡi", 350),                    # rưỡi = +50 of "trăm"
    ("mười rưỡi", 10.5),                       # rưỡi after non-100/1000 = 0.5
    ("một triệu", 1_000_000),
    ("một tỷ", 1_000_000_000),
    ("hai phẩy năm", 2.5),
    ("không phẩy một", 0.1),
    ("âm năm", -5),
])
def test_parse_thousands_and_specials(phrase, expected):
    assert parse_number_word(phrase) == pytest.approx(expected)
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Replace entire `parser_vn.py` with full implementation**

Replace `/Users/it/Documents/MySource/voiceApp/backend/app/services/parser_vn.py` with:

```python
"""Vietnamese number-word parser — full implementation."""
from __future__ import annotations

_DIGITS: dict[str, int] = {
    "không": 0, "một": 1, "hai": 2, "ba": 3, "bốn": 4,
    "năm": 5, "sáu": 6, "bảy": 7, "tám": 8, "chín": 9,
}

_UNIT_AFTER_MUOI: dict[str, int] = {**_DIGITS, "tư": 4, "lăm": 5, "mốt": 1}
_LE = {"lẻ", "linh"}

# Scale words and their values
_SCALES: dict[str, int] = {
    "nghìn": 1_000, "ngàn": 1_000,
    "triệu": 1_000_000,
    "tỷ": 1_000_000_000, "tỉ": 1_000_000_000,
}

# Order from largest to smallest for left-to-right parsing
_SCALE_ORDER = ["tỷ", "tỉ", "triệu", "nghìn", "ngàn"]


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())


def _parse_under_100(tokens: list[str]) -> int:
    if not tokens:
        raise ValueError("empty")
    if len(tokens) == 1:
        t = tokens[0]
        if t in _DIGITS:
            return _DIGITS[t]
        if t == "mười":
            return 10
        raise ValueError(f"unknown 0-9 token: {t!r}")
    if len(tokens) == 2:
        a, b = tokens
        if a == "mười":
            if b == "lăm":
                return 15
            if b in _DIGITS:
                return 10 + _DIGITS[b]
            raise ValueError(f"bad teen unit: {b!r}")
        if b == "mươi":
            if a in _DIGITS and _DIGITS[a] >= 2:
                return _DIGITS[a] * 10
            raise ValueError(f"bad tens prefix: {a!r}")
    if len(tokens) == 3 and tokens[1] == "mươi":
        a, _, c = tokens
        if a not in _DIGITS or _DIGITS[a] < 2:
            raise ValueError(f"bad tens prefix: {a!r}")
        unit = _UNIT_AFTER_MUOI.get(c)
        if unit is None:
            raise ValueError(f"bad unit: {c!r}")
        return _DIGITS[a] * 10 + unit
    raise ValueError(f"under-100 cannot parse: {tokens!r}")


def _parse_under_1000(tokens: list[str]) -> int:
    if "trăm" not in tokens:
        return _parse_under_100(tokens)
    idx = tokens.index("trăm")
    head, tail = tokens[:idx], tokens[idx + 1:]
    if not head:
        hundreds = 1
    elif len(head) == 1 and head[0] in _DIGITS:
        hundreds = _DIGITS[head[0]]
    else:
        raise ValueError(f"bad hundreds prefix: {head!r}")
    if not tail:
        return hundreds * 100
    if tail[0] in _LE:
        rest = tail[1:]
        if len(rest) != 1 or rest[0] not in _DIGITS:
            raise ValueError(f"bad 'lẻ' tail: {tail!r}")
        return hundreds * 100 + _DIGITS[rest[0]]
    return hundreds * 100 + _parse_under_100(tail)


def _split_at_first(tokens: list[str], target_set: set[str]) -> tuple[list[str], str, list[str]] | None:
    """Find the first occurrence of any token in target_set; return (head, found, tail) or None."""
    for i, t in enumerate(tokens):
        if t in target_set:
            return tokens[:i], t, tokens[i + 1:]
    return None


def _apply_ruoi(value: float, unit_token: str | None) -> float:
    """Add half of the named unit. unit_token in {nghìn, ngàn, triệu, tỷ, tỉ, trăm} or None for 0.5."""
    if unit_token is None:
        return value + 0.5
    halves = {
        "nghìn": 500, "ngàn": 500,
        "triệu": 500_000,
        "tỷ": 500_000_000, "tỉ": 500_000_000,
        "trăm": 50,
    }
    return value + halves[unit_token]


def _parse_positive(tokens: list[str]) -> float:
    """Parse positive number with possible scale words and 'rưỡi'/'phẩy'."""
    # Handle 'phẩy' (decimal point)
    if "phẩy" in tokens:
        idx = tokens.index("phẩy")
        whole = _parse_positive(tokens[:idx]) if tokens[:idx] else 0
        frac_tokens = tokens[idx + 1:]
        # decimal portion: read each digit
        frac_str = ""
        for t in frac_tokens:
            if t in _DIGITS:
                frac_str += str(_DIGITS[t])
            else:
                raise ValueError(f"bad decimal digit: {t!r}")
        return whole + float(f"0.{frac_str}") if frac_str else float(whole)

    # Handle trailing 'rưỡi'
    if tokens and tokens[-1] == "rưỡi":
        body = tokens[:-1]
        # find the last scale word in body to know the unit
        unit = None
        for t in reversed(body):
            if t in _SCALES or t == "trăm":
                unit = t
                break
        base = _parse_positive(body)
        return _apply_ruoi(base, unit)

    # Recursively split by scale words from largest to smallest
    for scale in _SCALE_ORDER:
        if scale in tokens:
            idx = tokens.index(scale)
            head = tokens[:idx]
            tail = tokens[idx + 1:]
            head_val = _parse_under_1000(head) if head else 1
            tail_val = _parse_positive(tail) if tail else 0
            return head_val * _SCALES[scale] + tail_val

    return _parse_under_1000(tokens)


def parse_number_word(text: str) -> float:
    text = _normalize(text)
    if not text:
        raise ValueError("empty input")
    tokens = text.split()
    if tokens and tokens[0] == "âm":
        return -_parse_positive(tokens[1:])
    return _parse_positive(tokens)


def parse_expression(text: str) -> tuple[list[float], float]:
    """Parse 'X cộng Y cộng Z bằng' → ([X, Y, Z], sum). Implemented in Task 13."""
    raise NotImplementedError
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_parser_vn.py -v
```

Expected: all previous + 11 new tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/services/parser_vn.py backend/tests/test_parser_vn.py
git commit -m "feat(parser): support thousands/millions/billions, rưỡi, phẩy, âm"
```

---

## Task 13: VN parser — expression parsing (delimiters + sum)

**Files:**
- Modify: `backend/app/services/parser_vn.py`
- Modify: `backend/tests/test_parser_vn.py`

- [ ] **Step 1: Add failing tests**

Append to `/Users/it/Documents/MySource/voiceApp/backend/tests/test_parser_vn.py`:

```python
def test_parse_expression_basic():
    nums, total = parse_expression("hai mươi ba cộng năm cộng mười hai bằng")
    assert nums == [23, 5, 12]
    assert total == 40


def test_parse_expression_with_hundreds_and_terminator():
    nums, total = parse_expression("hai mươi ba cộng năm cộng mười hai cộng trăm lẻ năm cộng mười tám bằng")
    assert nums == [23, 5, 12, 105, 18]
    assert total == 163


def test_parse_expression_no_terminator():
    nums, total = parse_expression("một cộng hai cộng ba")
    assert nums == [1, 2, 3]
    assert total == 6


def test_parse_expression_terminator_tong():
    nums, total = parse_expression("một cộng hai tổng")
    assert nums == [1, 2]
    assert total == 3


def test_parse_expression_terminator_equal_sign():
    nums, total = parse_expression("một cộng hai =")
    assert nums == [1, 2]
    assert total == 3


def test_parse_expression_punctuation_stripped():
    nums, total = parse_expression("một, cộng. hai!")
    assert nums == [1, 2]


def test_parse_expression_repeated_for_2a_rule():
    """Group rule '2a + 2c' is read as repeating the value twice."""
    nums, total = parse_expression("hai mươi ba cộng hai mươi ba cộng mười hai cộng mười hai bằng")
    assert nums == [23, 23, 12, 12]
    assert total == 70


def test_parse_expression_empty_raises():
    with pytest.raises(ValueError):
        parse_expression("")
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement `parse_expression`**

Replace the `parse_expression` function in `parser_vn.py` with:

```python
import re

_DELIMITERS = {"cộng", "+", "và", "với"}
_TERMINATORS = {"bằng", "=", "tổng", "kết", "thúc"}  # "kết thúc" two words; both kết alone OR together
_PUNCT_RE = re.compile(r"[,.!?;:]")


def parse_expression(text: str) -> tuple[list[float], float]:
    """Parse 'A cộng B cộng C bằng' into ([A,B,C], sum)."""
    text = _PUNCT_RE.sub(" ", text)
    text = _normalize(text)
    if not text:
        raise ValueError("empty expression")

    tokens = text.split()
    # Cut at terminator
    cut_idx = None
    for i, t in enumerate(tokens):
        if t in _TERMINATORS:
            cut_idx = i
            break
    if cut_idx is not None:
        tokens = tokens[:cut_idx]
    if not tokens:
        raise ValueError("no number tokens before terminator")

    # Split by delimiters
    parts: list[list[str]] = []
    current: list[str] = []
    for t in tokens:
        if t in _DELIMITERS:
            if current:
                parts.append(current)
                current = []
        else:
            current.append(t)
    if current:
        parts.append(current)

    if not parts:
        raise ValueError("no parseable parts")

    numbers: list[float] = []
    for part in parts:
        numbers.append(parse_number_word(" ".join(part)))
    return numbers, sum(numbers)
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_parser_vn.py -v
```

Expected: all previous + 8 expression tests pass.

- [ ] **Step 5: Run full parser test suite**

```bash
pytest tests/test_parser_vn.py -v
```

Expected: ~50 tests, all pass.

- [ ] **Step 6: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/services/parser_vn.py backend/tests/test_parser_vn.py
git commit -m "feat(parser): parse cộng-delimited expressions with bằng/= terminator"
```

---

## Task 14: Stub OCR & STT services

**Files:**
- Create: `backend/app/services/ocr.py`
- Create: `backend/app/services/stt.py`
- Create: `backend/tests/test_services_stubs.py`

- [ ] **Step 1: Write failing tests**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_services_stubs.py`:

```python
from app.services.ocr import OcrService, StubOcrService, OcrDetection
from app.services.stt import SttService, StubSttService


def test_stub_ocr_returns_fixed_detections():
    svc: OcrService = StubOcrService()
    detections = svc.extract(b"fake image bytes")
    assert len(detections) >= 1
    for d in detections:
        assert isinstance(d, OcrDetection)
        assert d.bbox.x >= 0
        assert d.value is not None


def test_stub_stt_returns_fixed_transcript():
    svc: SttService = StubSttService()
    result = svc.transcribe(b"fake audio bytes")
    assert result.transcript
    assert isinstance(result.transcript, str)
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement `services/ocr.py`**

Create `/Users/it/Documents/MySource/voiceApp/backend/app/services/ocr.py`:

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class BBox:
    x: float
    y: float
    w: float
    h: float


@dataclass(frozen=True)
class OcrDetection:
    bbox: BBox
    raw_text: str
    value: float | None
    confidence: float


class OcrService(Protocol):
    def extract(self, image_bytes: bytes) -> list[OcrDetection]: ...


class StubOcrService:
    """Returns a fixed set of fake detections — used until Plan 2 wires PaddleOCR."""

    def extract(self, image_bytes: bytes) -> list[OcrDetection]:
        return [
            OcrDetection(BBox(10, 20, 40, 30), "23", 23.0, 0.95),
            OcrDetection(BBox(80, 20, 30, 30), "5", 5.0, 0.92),
            OcrDetection(BBox(140, 20, 50, 30), "105", 105.0, 0.88),
        ]
```

- [ ] **Step 4: Implement `services/stt.py`**

Create `/Users/it/Documents/MySource/voiceApp/backend/app/services/stt.py`:

```python
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
```

- [ ] **Step 5: Run — expect PASS**

```bash
pytest tests/test_services_stubs.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/services/ocr.py backend/app/services/stt.py backend/tests/test_services_stubs.py
git commit -m "feat(services): add OcrService/SttService Protocols + Stub impls"
```

---

## Task 15: Pydantic schemas

**Files:**
- Create: `backend/app/schemas.py`
- Create: `backend/tests/test_schemas.py`

- [ ] **Step 1: Write failing tests**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_schemas.py`:

```python
import pytest
from pydantic import ValidationError
from app.schemas import (
    GroupDef, TemplateCreate, TemplateOut,
    CaptureCreateMeta, CaptureOut, OcrNumberOut, BBoxOut,
    ProvinceOut,
)


def test_group_def_valid_with_default_provinces():
    g = GroupDef(index=1, label="Lô", bet_type="lo", multiplier=80.0, default_provinces=["HN"])
    assert g.bet_type == "lo"
    assert g.default_provinces == ["HN"]


def test_group_def_default_provinces_optional_defaults_empty():
    g = GroupDef(index=1, label="Lô", bet_type="lo", multiplier=80.0)
    assert g.default_provinces == []


def test_group_def_invalid_bet_type():
    with pytest.raises(ValidationError):
        GroupDef(index=1, label="x", bet_type="bogus", multiplier=1.0)


def test_template_create_with_groups():
    t = TemplateCreate(name="T", groups=[
        GroupDef(index=1, label="L", bet_type="lo", multiplier=80.0, default_provinces=["HN"]),
        GroupDef(index=2, label="D", bet_type="de", multiplier=82.0, default_provinces=["HN"]),
    ])
    assert len(t.groups) == 2


def test_capture_create_meta_minimal():
    m = CaptureCreateMeta(template_id=1, group_provinces={1: ["HN"]})
    assert m.group_provinces == {1: ["HN"]}
    assert m.writer_name is None


def test_capture_create_meta_requires_at_least_one_group():
    with pytest.raises(ValidationError):
        CaptureCreateMeta(template_id=1, group_provinces={})


def test_capture_create_meta_rejects_empty_province_list_per_group():
    with pytest.raises(ValidationError):
        CaptureCreateMeta(template_id=1, group_provinces={1: []})


def test_province_out():
    p = ProvinceOut(code="HN", region="mb", name="Hà Nội")
    assert p.code == "HN"
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement `schemas.py`**

Create `/Users/it/Documents/MySource/voiceApp/backend/app/schemas.py`:

```python
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.domain.enums import BetType, CaptureStatus


class GroupDef(BaseModel):
    index: int = Field(ge=1)
    label: str
    bet_type: BetType
    multiplier: float = Field(gt=0)
    default_provinces: list[str] = Field(default_factory=list)


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    groups: list[GroupDef] = Field(min_length=1)


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    groups: list[GroupDef]
    created_at: datetime


class ProvinceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    region: str
    name: str


class BBoxOut(BaseModel):
    x: float
    y: float
    w: float
    h: float


class OcrNumberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    bbox: BBoxOut
    raw_text: str | None
    raw_value: float | None
    corrected_value: float | None
    confidence: float | None


class CaptureCreateMeta(BaseModel):
    template_id: int
    group_provinces: dict[int, list[str]] = Field(min_length=1)
    writer_name: str | None = None
    note_date: str | None = None  # YYYY-MM-DD
    tags: list[str] | None = None
    notes: str | None = None

    @field_validator("group_provinces")
    @classmethod
    def _validate_group_provinces(cls, v: dict[int, list[str]]) -> dict[int, list[str]]:
        for gi, provs in v.items():
            if not provs:
                raise ValueError(f"group {gi} must have at least one province")
            if any(not c.strip() for c in provs):
                raise ValueError(f"group {gi}: province codes must be non-empty")
        return v


class CaptureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    template_id: int
    image_path: str
    status: CaptureStatus
    final_value: float | None
    group_provinces: dict[int, list[str]]
    writer_name: str | None
    note_date: str | None
    tags: list[str] | None
    notes: str | None
    ocr_numbers: list[OcrNumberOut] = []
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_schemas.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/schemas.py backend/tests/test_schemas.py
git commit -m "feat(backend): add Pydantic schemas for Template, Capture, Province"
```

---

## Task 16: FastAPI app + dependencies + lifespan

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/test_main.py`

- [ ] **Step 1: Write failing test**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_main.py`:

```python
from fastapi.testclient import TestClient


def test_health_endpoint(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_openapi_doc_available(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    assert resp.json()["info"]["title"]
```

Add fixture to `conftest.py`. Append to `/Users/it/Documents/MySource/voiceApp/backend/tests/conftest.py`:

```python
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
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/test_main.py -v
```

Expected: FAIL — `cannot import 'create_app'`.

- [ ] **Step 3: Implement `api/__init__.py` (empty)**

Create `/Users/it/Documents/MySource/voiceApp/backend/app/api/__init__.py` (empty).

- [ ] **Step 4: Implement `api/deps.py`**

Create `/Users/it/Documents/MySource/voiceApp/backend/app/api/deps.py`:

```python
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
```

- [ ] **Step 5: Implement `main.py`**

Create `/Users/it/Documents/MySource/voiceApp/backend/app/main.py`:

```python
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db import Base
from app.api.deps import _SessionLocal, _engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ensure media + db dirs
    Path(settings.media_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    # import models so metadata is populated
    from app import models  # noqa: F401
    Base.metadata.create_all(_engine)
    # seed provinces if empty
    from app.seed import seed_provinces
    with _SessionLocal() as s:
        seed_provinces(s)
        s.commit()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="VoiceApp Backend", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 6: Run — expect PASS**

```bash
pytest tests/test_main.py -v
```

Expected: 2 passed.

- [ ] **Step 7: Verify uvicorn boots**

```bash
cd /Users/it/Documents/MySource/voiceApp/backend
source .venv/bin/activate
uvicorn app.main:app --port 8000 &
sleep 2
curl -s http://localhost:8000/api/health
kill %1
```

Expected: `{"status":"ok"}`.

- [ ] **Step 8: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/api/__init__.py backend/app/api/deps.py backend/app/main.py backend/tests/test_main.py backend/tests/conftest.py
git commit -m "feat(backend): FastAPI app with lifespan DB init + province seed + health endpoint"
```

---

## Task 17: API — GET /api/provinces

**Files:**
- Create: `backend/app/api/provinces.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_api_provinces.py`

- [ ] **Step 1: Write failing test**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_api_provinces.py`:

```python
def test_list_provinces_seeded(client, db_session):
    # the lifespan-equivalent seeding hasn't run for the test client (we use direct session),
    # so seed manually
    from app.seed import seed_provinces
    seed_provinces(db_session)
    db_session.commit()

    resp = client.get("/api/provinces")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 3
    codes = {p["code"] for p in data}
    assert {"HN", "DNG", "KH"}.issubset(codes)


def test_list_provinces_filter_by_region(client, db_session):
    from app.seed import seed_provinces
    seed_provinces(db_session)
    db_session.commit()

    resp = client.get("/api/provinces?region=mb")
    assert resp.status_code == 200
    data = resp.json()
    assert all(p["region"] == "mb" for p in data)
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement endpoint**

Create `/Users/it/Documents/MySource/voiceApp/backend/app/api/provinces.py`:

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models import Province
from app.schemas import ProvinceOut


router = APIRouter(prefix="/api/provinces", tags=["provinces"])


@router.get("", response_model=list[ProvinceOut])
def list_provinces(
    region: str | None = Query(default=None, pattern="^(mb|mt|mn)$"),
    db: Session = Depends(get_db),
):
    q = db.query(Province)
    if region:
        q = q.filter(Province.region == region)
    return q.order_by(Province.region, Province.code).all()
```

- [ ] **Step 4: Wire router in `main.py`**

Edit `/Users/it/Documents/MySource/voiceApp/backend/app/main.py`. After the `health()` definition, before `return app`, add:

```python
    from app.api.provinces import router as provinces_router
    app.include_router(provinces_router)
```

- [ ] **Step 5: Run — expect PASS**

```bash
pytest tests/test_api_provinces.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/api/provinces.py backend/app/main.py backend/tests/test_api_provinces.py
git commit -m "feat(api): GET /api/provinces with optional region filter"
```

---

## Task 18: API — Templates CRUD

**Files:**
- Create: `backend/app/api/templates.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_api_templates.py`

- [ ] **Step 1: Write failing tests**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_api_templates.py`:

```python
def test_create_template(client):
    body = {
        "name": "Lô-Đề-Xiên",
        "groups": [
            {"index": 1, "label": "Lô", "bet_type": "lo", "multiplier": 80.0},
            {"index": 2, "label": "Đề", "bet_type": "de", "multiplier": 82.0},
            {"index": 3, "label": "Xiên 2", "bet_type": "xien_2", "multiplier": 14.5},
        ],
    }
    resp = client.post("/api/templates", json=body)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["id"] >= 1
    assert data["name"] == "Lô-Đề-Xiên"
    assert len(data["groups"]) == 3
    assert data["groups"][1]["bet_type"] == "de"


def test_list_templates(client):
    client.post("/api/templates", json={
        "name": "T1",
        "groups": [{"index": 1, "label": "G", "bet_type": "lo", "multiplier": 80.0}],
    })
    client.post("/api/templates", json={
        "name": "T2",
        "groups": [{"index": 1, "label": "G", "bet_type": "de", "multiplier": 82.0}],
    })
    resp = client.get("/api/templates")
    assert resp.status_code == 200
    names = [t["name"] for t in resp.json()]
    assert "T1" in names and "T2" in names


def test_get_template_by_id(client):
    r = client.post("/api/templates", json={
        "name": "T", "groups": [{"index": 1, "label": "G", "bet_type": "lo", "multiplier": 80.0}],
    })
    tid = r.json()["id"]
    resp = client.get(f"/api/templates/{tid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == tid


def test_get_template_404(client):
    resp = client.get("/api/templates/999")
    assert resp.status_code == 404


def test_create_template_invalid_bet_type_400(client):
    resp = client.post("/api/templates", json={
        "name": "X", "groups": [{"index": 1, "label": "G", "bet_type": "bogus", "multiplier": 1.0}],
    })
    assert resp.status_code == 422
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement endpoint**

Create `/Users/it/Documents/MySource/voiceApp/backend/app/api/templates.py`:

```python
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models import Template
from app.schemas import TemplateCreate, TemplateOut, GroupDef


router = APIRouter(prefix="/api/templates", tags=["templates"])


def _to_out(t: Template) -> TemplateOut:
    raw_groups = json.loads(t.groups_json)
    groups = [GroupDef(**g) for g in raw_groups]
    return TemplateOut(id=t.id, name=t.name, groups=groups, created_at=t.created_at)


@router.post("", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(body: TemplateCreate, db: Session = Depends(get_db)) -> TemplateOut:
    t = Template(
        name=body.name,
        groups_json=json.dumps([g.model_dump(mode="json") for g in body.groups]),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _to_out(t)


@router.get("", response_model=list[TemplateOut])
def list_templates(db: Session = Depends(get_db)) -> list[TemplateOut]:
    return [_to_out(t) for t in db.query(Template).order_by(Template.id.desc()).all()]


@router.get("/{template_id}", response_model=TemplateOut)
def get_template(template_id: int, db: Session = Depends(get_db)) -> TemplateOut:
    t = db.get(Template, template_id)
    if t is None:
        raise HTTPException(status_code=404, detail="template not found")
    return _to_out(t)
```

- [ ] **Step 4: Wire router in `main.py`**

Edit `/Users/it/Documents/MySource/voiceApp/backend/app/main.py`. Just below the `provinces_router` line, add:

```python
    from app.api.templates import router as templates_router
    app.include_router(templates_router)
```

- [ ] **Step 5: Run — expect PASS**

```bash
pytest tests/test_api_templates.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/api/templates.py backend/app/main.py backend/tests/test_api_templates.py
git commit -m "feat(api): templates CRUD (create, list, get-by-id)"
```

---

## Task 19: API — Captures (with stub OCR)

**Files:**
- Create: `backend/app/api/captures.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_api_captures.py`

- [ ] **Step 1: Write failing tests**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_api_captures.py`:

```python
import io


def _create_template(client) -> int:
    r = client.post("/api/templates", json={
        "name": "T",
        "groups": [{"index": 1, "label": "G", "bet_type": "lo", "multiplier": 80.0}],
    })
    return r.json()["id"]


def test_create_capture_with_stub_ocr(client):
    tid = _create_template(client)
    img_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    files = {"image": ("note.png", io.BytesIO(img_bytes), "image/png")}
    # group_provinces as JSON string in form
    data = {"template_id": str(tid), "group_provinces": '{"1": ["HN"]}'}
    resp = client.post("/api/captures", files=files, data=data)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["id"] >= 1
    assert body["status"] == "draft"
    assert body["group_provinces"] == {"1": ["HN"]}
    assert len(body["ocr_numbers"]) >= 1
    assert body["ocr_numbers"][0]["raw_value"] is not None


def test_create_capture_mixed_per_group_provinces(client):
    """Group 1 = HN only; Group 3 = DNG+KH (matches spec §17 worked example)."""
    tid = _create_template(client)
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    data = {
        "template_id": str(tid),
        "group_provinces": '{"1": ["HN"], "2": ["HN"], "3": ["DNG", "KH"]}',
    }
    resp = client.post("/api/captures", files=files, data=data)
    assert resp.status_code == 201, resp.text
    gp = resp.json()["group_provinces"]
    assert gp == {"1": ["HN"], "2": ["HN"], "3": ["DNG", "KH"]}


def test_create_capture_invalid_group_provinces_json(client):
    tid = _create_template(client)
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    resp = client.post("/api/captures", files=files,
                       data={"template_id": str(tid), "group_provinces": "not-json"})
    assert resp.status_code == 422


def test_create_capture_empty_group_provinces_rejected(client):
    tid = _create_template(client)
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    resp = client.post("/api/captures", files=files,
                       data={"template_id": str(tid), "group_provinces": "{}"})
    assert resp.status_code == 422


def test_list_captures(client):
    tid = _create_template(client)
    for _ in range(2):
        files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
        client.post("/api/captures", files=files,
                    data={"template_id": str(tid), "group_provinces": '{"1": ["HN"]}'})

    resp = client.get("/api/captures")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_capture_by_id(client):
    tid = _create_template(client)
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    r = client.post("/api/captures", files=files,
                    data={"template_id": str(tid), "group_provinces": '{"1": ["HN"]}'})
    cid = r.json()["id"]

    resp = client.get(f"/api/captures/{cid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == cid


def test_capture_unknown_template_404(client):
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    resp = client.post("/api/captures", files=files,
                       data={"template_id": "999", "group_provinces": '{"1": ["HN"]}'})
    assert resp.status_code == 404
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement endpoint**

Create `/Users/it/Documents/MySource/voiceApp/backend/app/api/captures.py`:

```python
import json
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_ocr_service
from app.config import settings
from app.models import Template, Capture, OcrNumber
from app.schemas import CaptureOut, OcrNumberOut, BBoxOut
from app.services.ocr import OcrService


router = APIRouter(prefix="/api/captures", tags=["captures"])


def _capture_to_out(c: Capture) -> CaptureOut:
    raw_gp = json.loads(c.group_provinces_json)
    # JSON keys are str → coerce back to int for the response model
    group_provinces: dict[int, list[str]] = {int(k): v for k, v in raw_gp.items()}
    return CaptureOut(
        id=c.id,
        template_id=c.template_id,
        image_path=c.image_path,
        status=c.status,
        final_value=c.final_value,
        group_provinces=group_provinces,
        writer_name=c.writer_name,
        note_date=c.note_date,
        tags=json.loads(c.tags_json) if c.tags_json else None,
        notes=c.notes,
        ocr_numbers=[
            OcrNumberOut(
                id=n.id,
                bbox=BBoxOut(x=n.bbox_x, y=n.bbox_y, w=n.bbox_w, h=n.bbox_h),
                raw_text=n.raw_text,
                raw_value=n.raw_value,
                corrected_value=n.corrected_value,
                confidence=n.confidence,
            )
            for n in (c.ocr_numbers if hasattr(c, "ocr_numbers") else _load_ocr(c))
        ],
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def _load_ocr(c: Capture):
    """Helper for when relationship not configured (we didn't add it)."""
    return []


@router.post("", response_model=CaptureOut, status_code=status.HTTP_201_CREATED)
def create_capture(
    template_id: int = Form(...),
    group_provinces: str = Form(..., description='JSON dict, e.g. {"1": ["HN"], "3": ["DNG","KH"]}'),
    writer_name: str | None = Form(default=None),
    note_date: str | None = Form(default=None),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    ocr: OcrService = Depends(get_ocr_service),
) -> CaptureOut:
    t = db.get(Template, template_id)
    if t is None:
        raise HTTPException(status_code=404, detail="template not found")

    try:
        gp_raw = json.loads(group_provinces)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="group_provinces must be valid JSON")

    if not isinstance(gp_raw, dict) or not gp_raw:
        raise HTTPException(status_code=422, detail="group_provinces must be a non-empty object")

    # normalize keys to str (we store as JSON dict, keys are strings)
    gp_normalized: dict[str, list[str]] = {}
    for k, v in gp_raw.items():
        if not isinstance(v, list) or not v:
            raise HTTPException(status_code=422, detail=f"group {k}: provinces list must be non-empty")
        gp_normalized[str(k)] = [p.strip() for p in v if isinstance(p, str) and p.strip()]
        if not gp_normalized[str(k)]:
            raise HTTPException(status_code=422, detail=f"group {k}: no valid province codes")

    # Save image
    Path(settings.media_dir, "captures").mkdir(parents=True, exist_ok=True)
    ext = (image.filename or "img").split(".")[-1] if "." in (image.filename or "") else "bin"
    fname = f"{uuid.uuid4().hex}.{ext}"
    fpath = Path(settings.media_dir, "captures", fname)
    image_bytes = image.file.read()
    fpath.write_bytes(image_bytes)

    # Run OCR (stub for now)
    detections = ocr.extract(image_bytes)

    c = Capture(
        template_id=template_id,
        image_path=str(fpath),
        status="draft",
        group_provinces_json=json.dumps(gp_normalized),
        writer_name=writer_name,
        note_date=note_date,
    )
    db.add(c)
    db.flush()  # need c.id

    ocr_rows: list[OcrNumber] = []
    for d in detections:
        n = OcrNumber(
            capture_id=c.id,
            bbox_x=d.bbox.x, bbox_y=d.bbox.y, bbox_w=d.bbox.w, bbox_h=d.bbox.h,
            raw_text=d.raw_text,
            raw_value=d.value,
            confidence=d.confidence,
        )
        db.add(n)
        ocr_rows.append(n)
    db.commit()
    db.refresh(c)
    for n in ocr_rows:
        db.refresh(n)

    # Manually attach for serializer
    c.ocr_numbers = ocr_rows  # type: ignore[attr-defined]
    return _capture_to_out(c)


@router.get("", response_model=list[CaptureOut])
def list_captures(db: Session = Depends(get_db)) -> list[CaptureOut]:
    out: list[CaptureOut] = []
    for c in db.query(Capture).order_by(Capture.id.desc()).all():
        c.ocr_numbers = db.query(OcrNumber).filter(OcrNumber.capture_id == c.id).all()  # type: ignore
        out.append(_capture_to_out(c))
    return out


@router.get("/{capture_id}", response_model=CaptureOut)
def get_capture(capture_id: int, db: Session = Depends(get_db)) -> CaptureOut:
    c = db.get(Capture, capture_id)
    if c is None:
        raise HTTPException(status_code=404, detail="capture not found")
    c.ocr_numbers = db.query(OcrNumber).filter(OcrNumber.capture_id == c.id).all()  # type: ignore
    return _capture_to_out(c)
```

- [ ] **Step 4: Wire router in `main.py`**

Edit `/Users/it/Documents/MySource/voiceApp/backend/app/main.py`. Below the `templates_router` line, add:

```python
    from app.api.captures import router as captures_router
    app.include_router(captures_router)
```

- [ ] **Step 5: Run — expect PASS**

```bash
pytest tests/test_api_captures.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/api/captures.py backend/app/main.py backend/tests/test_api_captures.py
git commit -m "feat(api): captures create/list/get with stub OCR + multi-province + media storage"
```

---

## Task 20: End-to-end smoke verification

**Files:** none (manual verification only)

- [ ] **Step 1: Run full test suite**

```bash
cd /Users/it/Documents/MySource/voiceApp/backend
source .venv/bin/activate
pytest -v
```

Expected: tất cả test pass (~60+ tests across enums, db, models, parser, schemas, stubs, main, provinces, templates, captures).

- [ ] **Step 2: Boot real server + smoke curl**

```bash
cd /Users/it/Documents/MySource/voiceApp/backend
source .venv/bin/activate
uvicorn app.main:app --port 8000 &
sleep 2

# health
curl -s http://localhost:8000/api/health | tee /dev/stderr

# provinces (after lifespan seeding)
curl -s "http://localhost:8000/api/provinces?region=mt" | head -c 500

# create template
TID=$(curl -s -X POST http://localhost:8000/api/templates \
  -H 'content-type: application/json' \
  -d '{"name":"smoke","groups":[{"index":1,"label":"L","bet_type":"lo","multiplier":80}]}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
echo "template id: $TID"

# create capture (stub OCR) — group 1 đặt HN, không có multi-province trong smoke
echo fake-image > /tmp/fake.png
curl -s -X POST http://localhost:8000/api/captures \
  -F "template_id=$TID" \
  -F 'group_provinces={"1": ["HN"]}' \
  -F "image=@/tmp/fake.png" | head -c 500

kill %1 2>/dev/null || true
rm /tmp/fake.png
```

Expected output snippets:
- `{"status":"ok"}`
- JSON list province with region=mt
- A non-empty template id
- A capture JSON with `"status":"draft"`, `"provinces":["DNG","KH"]`, and `ocr_numbers` array of length ≥ 1.

- [ ] **Step 3: Confirm DB file created**

```bash
ls -la /Users/it/Documents/MySource/voiceApp/backend/data/voiceapp.db
ls /Users/it/Documents/MySource/voiceApp/backend/data/media/captures | head
```

Expected: db file exists; at least 1 image file in `media/captures/`.

- [ ] **Step 4: Commit any leftover (if pytest auto-fixed lints, etc.)**

```bash
cd /Users/it/Documents/MySource/voiceApp
git status
# if anything dirty:
git add -A && git commit -m "chore: end-of-plan-1 cleanup"
```

- [ ] **Step 5: Tag plan completion**

```bash
git tag plan-1-complete
```

---

## Verification Checklist (end of Plan 1)

- [ ] `pytest -v` passes 60+ tests across all modules.
- [ ] `uvicorn app.main:app` boots without error.
- [ ] `GET /api/health` returns `{"status":"ok"}`.
- [ ] `GET /api/provinces` returns ≥ 36 provinces seeded across 3 regions.
- [ ] `POST /api/templates` creates with all 7 `bet_type` accepted; `bogus` rejected with 422.
- [ ] `POST /api/captures` accepts per-group provinces (vd `{"1":["HN"], "3":["DNG","KH"]}`) + image upload; persists OcrNumber rows from stub.
- [ ] DB file created at `backend/data/voiceapp.db`; image saved at `backend/data/media/captures/<uuid>.png`.
- [ ] Vietnamese parser handles: digits, teens, tens (with tư/lăm/mốt), hundreds (with lẻ/linh), thousands/millions/billions, rưỡi, phẩy, âm, expression with cộng + bằng/tổng/=.

## What Plan 1 explicitly does NOT do (deferred to Plan 2+)

- ❌ Real PaddleOCR integration (Plan 2)
- ❌ Real Whisper STT (Plan 2)
- ❌ Audio upload endpoint (Plan 2)
- ❌ Match engine (Plan 3)
- ❌ Finalize endpoint (Plan 3)
- ❌ OCR correction PATCH endpoint (Plan 3)
- ❌ Lottery draws + settlement (Plan 11)
- ❌ Frontend (Plans 4-6)
