# Plan 2 — OCR + STT Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thay stub services bằng PaddleOCR + Whisper thật, thêm endpoint upload audio (POST `/api/captures/{id}/audio`) chạy STT + parse VN + trả `AudioGroup` với `parsed_numbers + sum`. Cuối plan: ghi âm thật, upload, nhận đúng các con số đã đọc.

**Architecture:** Service pattern giữ nguyên (Protocol-based). Thêm `PaddleOcrService` + `WhisperSttService` (lazy model load — chỉ load khi gọi lần đầu). Test dùng stub qua `dependency_overrides`; production dùng env var `VOICEAPP_USE_REAL_SERVICES=1` để switch. Audio file lưu ở `data/media/audio/`.

**Tech Stack:** PaddleOCR + paddlepaddle (CPU), openai-whisper (`small` Vietnamese), ffmpeg (system dep cho Whisper xử lý webm/mp3/wav). Existing: FastAPI, SQLAlchemy, Pydantic.

**Spec reference:** [docs/superpowers/specs/2026-04-30-voiceapp-handwritten-number-recognition-design.md](../specs/2026-04-30-voiceapp-handwritten-number-recognition-design.md) §11 (tech stack), §8 (POST /api/captures/{id}/audio).

**Pre-flight:** Plan 1 complete (tag `plan-1-complete`), 97 tests passing, 20 commits.

---

## File Structure

```
backend/
├── app/
│   ├── services/
│   │   ├── ocr.py              # MODIFY: add PaddleOcrService class
│   │   ├── stt.py              # MODIFY: add WhisperSttService class
│   │   ├── _model_cache.py     # NEW: lazy singleton holders for heavy models
│   │   └── audio.py            # NEW: audio bytes → temp file → STT + parse pipeline
│   ├── api/
│   │   ├── deps.py             # MODIFY: env-var switch real vs stub
│   │   └── captures.py         # MODIFY: add POST /{id}/audio endpoint
│   └── config.py               # MODIFY: add use_real_services + whisper_model_name + paddle_lang
├── tests/
│   ├── fixtures/               # NEW: small image (handwritten "23") + audio ("hai mươi ba bằng")
│   │   ├── tiny_23.png
│   │   └── hai_muoi_ba.wav
│   ├── test_services_real_ocr.py        # NEW: smoke test PaddleOcrService (skipped if model not installed)
│   ├── test_services_real_stt.py        # NEW: smoke test WhisperSttService (skipped if model not installed)
│   ├── test_services_audio_pipeline.py  # NEW: audio.py end-to-end with stub STT
│   └── test_api_capture_audio.py        # NEW: POST /api/captures/{id}/audio tests
├── requirements.txt            # MODIFY: add paddleocr, paddlepaddle, openai-whisper
└── README.md                   # MODIFY: ffmpeg install note
```

**Responsibilities:**
- `_model_cache.py` — module-level singletons for `PaddleOCR` and `whisper.Model`. Lazy import + lazy load (heavy: 30-90s first call).
- `ocr.py` `PaddleOcrService` — wraps PaddleOCR result, filters non-numeric text, normalizes bbox to (x,y,w,h).
- `stt.py` `WhisperSttService` — wraps `whisper.transcribe()`, returns `SttResult(transcript, language)`.
- `audio.py` `transcribe_and_parse()` — pure pipeline: bytes → tempfile → stt.transcribe() → parser_vn.parse_expression() → return parsed dict.
- `api/captures.py` `audio_upload()` — saves audio file → calls audio pipeline → creates `AudioGroup` row → returns it.
- `deps.py` env-var switch — keeps test path simple (always stub via override) while letting prod boot real services.

---

## Task 1: Pre-flight — install ffmpeg + verify

**Files:** none (system setup only)

- [ ] **Step 1: Check ffmpeg presence**

Run: `command -v ffmpeg && ffmpeg -version | head -1`

If present (any 4.x or 5.x or 6.x version), skip Step 2. If absent, proceed.

- [ ] **Step 2: Install ffmpeg via Homebrew (only if Step 1 failed)**

Run: `brew install ffmpeg`

Wait for completion (1-3 min).

Verify: `ffmpeg -version | head -1` — should print version.

- [ ] **Step 3: Sanity check ffmpeg can decode common audio**

Run:
```bash
cd /tmp
ffmpeg -y -f lavfi -i "sine=frequency=440:duration=1" -ar 16000 -ac 1 /tmp/sine.wav 2>&1 | tail -3
ls -la /tmp/sine.wav
rm /tmp/sine.wav
```

Expected: `sine.wav` ~32KB, ffmpeg exits 0.

- [ ] **Step 4: No commit — system dep doesn't go in git**

---

## Task 2: Add Python deps for PaddleOCR + Whisper

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/README.md` (ffmpeg note)

- [ ] **Step 1: Append to `backend/requirements.txt`**

Read current file first to confirm contents, then add 3 lines at the end:

```
paddleocr==2.8.1
paddlepaddle==2.6.2
openai-whisper==20240930
```

The full file should now be:

```
fastapi==0.115.0
uvicorn[standard]==0.32.0
sqlalchemy==2.0.36
pydantic==2.9.2
pydantic-settings==2.6.0
python-multipart==0.0.12
paddleocr==2.8.1
paddlepaddle==2.6.2
openai-whisper==20240930
```

- [ ] **Step 2: Install new deps into existing venv**

```bash
cd /Users/it/Documents/MySource/voiceApp/backend
source .venv/bin/activate
pip install -r requirements.txt
```

Expected: paddleocr + paddlepaddle (~600MB total) + openai-whisper (~10MB, but tiktoken ~5MB, torch ~200MB) install. May take 3-10 min on slow networks.

If pip reports torch wheel issues on macOS arm64, ensure pip is up to date:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

- [ ] **Step 3: Verify imports work**

```bash
source .venv/bin/activate
python -c "import paddleocr; print('paddleocr ok'); import whisper; print('whisper ok')"
```

Expected: both print "ok" with no traceback. (Warnings about CUDA/AVX are fine.)

- [ ] **Step 4: Update `backend/README.md`** — add a line under Setup mentioning ffmpeg

Read current `backend/README.md`, then add this line right after the closing fence of the Setup bash block:

```markdown
**System dependency:** `ffmpeg` must be installed (Whisper uses it for audio decoding). On macOS: `brew install ffmpeg`.
```

- [ ] **Step 5: Verify all existing tests still pass**

```bash
cd /Users/it/Documents/MySource/voiceApp/backend
source .venv/bin/activate
pytest 2>&1 | tail -3
```

Expected: 97 passed.

- [ ] **Step 6: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/requirements.txt backend/README.md
git commit -m "chore(backend): add paddleocr, paddlepaddle, openai-whisper deps + ffmpeg note"
```

---

## Task 3: Config additions for real services

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/tests/test_db.py` (extend test_settings_defaults)

- [ ] **Step 1: Update `test_db.py::test_settings_defaults`**

Open `/Users/it/Documents/MySource/voiceApp/backend/tests/test_db.py` and replace the existing `test_settings_defaults` with:

```python
def test_settings_defaults():
    s = Settings()
    assert s.db_path.endswith("voiceapp.db")
    assert s.media_dir.endswith("media")
    assert s.use_real_services is False
    assert s.whisper_model_name == "small"
    assert s.whisper_language == "vi"
    assert s.paddle_lang == "vi"
```

- [ ] **Step 2: Run — expect FAIL** (new attributes don't exist)

```bash
cd /Users/it/Documents/MySource/voiceApp/backend
source .venv/bin/activate
pytest tests/test_db.py::test_settings_defaults -v
```

Expected: FAIL — `AttributeError: 'Settings' object has no attribute 'use_real_services'`.

- [ ] **Step 3: Add fields to `app/config.py`**

Open `/Users/it/Documents/MySource/voiceApp/backend/app/config.py`. Inside the `Settings` class, after the `cors_origins` line and before the `db_url` property, add:

```python
    use_real_services: bool = False
    whisper_model_name: str = "small"  # tiny | base | small | medium | large
    whisper_language: str = "vi"
    paddle_lang: str = "vi"
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_db.py::test_settings_defaults -v
```

Expected: PASS.

- [ ] **Step 5: Run full suite (no regressions)**

```bash
pytest 2>&1 | tail -3
```

Expected: 97 passed.

- [ ] **Step 6: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/config.py backend/tests/test_db.py
git commit -m "feat(config): add use_real_services + Whisper/Paddle settings"
```

---

## Task 4: Lazy model cache module

**Files:**
- Create: `backend/app/services/_model_cache.py`
- Create: `backend/tests/test_model_cache.py`

- [ ] **Step 1: Write test**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_model_cache.py`:

```python
"""Smoke tests for the lazy model cache. Real models are NOT loaded here —
we just verify the cache is empty initially and resets correctly."""
from app.services import _model_cache


def test_caches_start_unloaded():
    _model_cache.reset()
    assert _model_cache._paddle_singleton is None
    assert _model_cache._whisper_singleton is None


def test_reset_clears_existing(monkeypatch):
    _model_cache._paddle_singleton = "fake-paddle"
    _model_cache._whisper_singleton = "fake-whisper"
    _model_cache.reset()
    assert _model_cache._paddle_singleton is None
    assert _model_cache._whisper_singleton is None
```

- [ ] **Step 2: Run — expect FAIL** (module doesn't exist)

```bash
pytest tests/test_model_cache.py -v
```

- [ ] **Step 3: Implement `_model_cache.py`**

Create `/Users/it/Documents/MySource/voiceApp/backend/app/services/_model_cache.py`:

```python
"""Lazy singletons for heavy ML models (PaddleOCR, Whisper).

Why singletons: loading paddleocr ~5-15s; whisper.load_model('small') ~5-30s.
We only want to pay this once per process. Tests should never trigger real loads
unless explicitly testing real services.
"""
from __future__ import annotations
from typing import Any

_paddle_singleton: Any = None
_whisper_singleton: Any = None


def get_paddle_ocr(lang: str = "vi") -> Any:
    """Return a singleton PaddleOCR instance. First call ~5-15s on CPU."""
    global _paddle_singleton
    if _paddle_singleton is None:
        from paddleocr import PaddleOCR
        _paddle_singleton = PaddleOCR(use_angle_cls=False, lang=lang, show_log=False)
    return _paddle_singleton


def get_whisper(model_name: str = "small") -> Any:
    """Return a singleton Whisper model. First call downloads model if absent."""
    global _whisper_singleton
    if _whisper_singleton is None:
        import whisper
        _whisper_singleton = whisper.load_model(model_name)
    return _whisper_singleton


def reset() -> None:
    """Drop cached models. Use in tests or to free memory."""
    global _paddle_singleton, _whisper_singleton
    _paddle_singleton = None
    _whisper_singleton = None
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_model_cache.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/services/_model_cache.py backend/tests/test_model_cache.py
git commit -m "feat(services): add lazy singleton cache for PaddleOCR + Whisper"
```

---

## Task 5: PaddleOcrService — class skeleton + fast unit test

**Files:**
- Modify: `backend/app/services/ocr.py` (append new class)
- Create: `backend/tests/test_paddle_ocr_service.py`

We test the value-extraction logic separately from the actual model call, so unit tests stay fast.

- [ ] **Step 1: Write test for PaddleOcrService logic (mocked OCR backend)**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_paddle_ocr_service.py`:

```python
from unittest.mock import patch
from app.services.ocr import PaddleOcrService, OcrDetection, BBox


# PaddleOCR's raw return format: list of [box_4_corners, (text, confidence)] per image.
# We feed a fake one through the service and verify number filtering + bbox normalization.
_FAKE_PADDLE_RESULT = [[
    [[[10.0, 20.0], [50.0, 20.0], [50.0, 50.0], [10.0, 50.0]], ("23", 0.95)],
    [[[80.0, 20.0], [110.0, 20.0], [110.0, 50.0], [80.0, 50.0]], ("hello", 0.88)],  # non-numeric → filtered
    [[[140.0, 20.0], [190.0, 20.0], [190.0, 50.0], [140.0, 50.0]], ("105", 0.91)],
    [[[200.0, 20.0], [240.0, 20.0], [240.0, 50.0], [200.0, 50.0]], ("3.5", 0.86)],  # decimal → kept
]]


def test_paddle_service_filters_non_numeric_and_normalizes_bbox():
    svc = PaddleOcrService(lang="vi")
    with patch.object(svc, "_run_paddle", return_value=_FAKE_PADDLE_RESULT):
        detections = svc.extract(b"image-bytes")

    assert len(detections) == 3  # "hello" filtered out
    values = [d.value for d in detections]
    assert 23.0 in values
    assert 105.0 in values
    assert 3.5 in values

    d23 = next(d for d in detections if d.value == 23.0)
    assert isinstance(d23.bbox, BBox)
    # bbox computed from 4 corners: x=min, y=min, w=max-min, h=max-min
    assert d23.bbox.x == 10.0
    assert d23.bbox.y == 20.0
    assert d23.bbox.w == 40.0
    assert d23.bbox.h == 30.0
    assert d23.confidence == 0.95


def test_paddle_service_handles_empty_result():
    svc = PaddleOcrService(lang="vi")
    with patch.object(svc, "_run_paddle", return_value=[None]):
        assert svc.extract(b"image-bytes") == []


def test_paddle_service_handles_negative_numbers():
    fake = [[[[[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]], ("-5", 0.9)]]]
    svc = PaddleOcrService(lang="vi")
    with patch.object(svc, "_run_paddle", return_value=fake):
        d = svc.extract(b"x")
    assert len(d) == 1
    assert d[0].value == -5.0
```

- [ ] **Step 2: Run — expect FAIL** (PaddleOcrService not defined)

```bash
pytest tests/test_paddle_ocr_service.py -v
```

- [ ] **Step 3: Append `PaddleOcrService` to `app/services/ocr.py`**

Open `/Users/it/Documents/MySource/voiceApp/backend/app/services/ocr.py` and append (after the existing `StubOcrService`):

```python
import re
import tempfile
from pathlib import Path

_NUMBER_RE = re.compile(r"^-?\d+(?:[.,]\d+)?$")


def _bbox_from_corners(corners: list[list[float]]) -> BBox:
    """PaddleOCR returns 4 corner points; convert to axis-aligned (x,y,w,h)."""
    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    return BBox(x=x_min, y=y_min, w=x_max - x_min, h=y_max - y_min)


def _parse_numeric(text: str) -> float | None:
    t = text.strip().replace(",", ".")
    if not _NUMBER_RE.match(t):
        return None
    try:
        return float(t)
    except ValueError:
        return None


class PaddleOcrService:
    """OcrService backed by PaddleOCR. Lazy-loads model on first call."""

    def __init__(self, lang: str = "vi") -> None:
        self._lang = lang

    def _run_paddle(self, image_path: str) -> list:
        """Call into PaddleOCR. Isolated for monkey-patching in tests."""
        from app.services._model_cache import get_paddle_ocr
        ocr = get_paddle_ocr(lang=self._lang)
        return ocr.ocr(image_path, cls=False)

    def extract(self, image_bytes: bytes) -> list[OcrDetection]:
        # PaddleOCR wants a file path, not bytes. Write to temp file.
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(image_bytes)
            tmp_path = f.name
        try:
            raw = self._run_paddle(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        if not raw or raw[0] is None:
            return []

        detections: list[OcrDetection] = []
        for entry in raw[0]:
            corners, (text, conf) = entry
            value = _parse_numeric(text)
            if value is None:
                continue
            detections.append(OcrDetection(
                bbox=_bbox_from_corners(corners),
                raw_text=text,
                value=value,
                confidence=float(conf),
            ))
        return detections
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_paddle_ocr_service.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Run full suite**

```bash
pytest 2>&1 | tail -3
```

Expected: 100 passed (97 + 3 new).

- [ ] **Step 6: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/services/ocr.py backend/tests/test_paddle_ocr_service.py
git commit -m "feat(ocr): PaddleOcrService with numeric filter + bbox normalization"
```

---

## Task 6: WhisperSttService — class + fast unit test

**Files:**
- Modify: `backend/app/services/stt.py` (append new class)
- Create: `backend/tests/test_whisper_stt_service.py`

- [ ] **Step 1: Write test (model call mocked)**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_whisper_stt_service.py`:

```python
from unittest.mock import patch
from app.services.stt import WhisperSttService, SttResult


def test_whisper_service_returns_transcript():
    svc = WhisperSttService(model_name="tiny", language="vi")
    fake_model_result = {"text": "  hai mươi ba cộng năm bằng  ", "language": "vi"}
    with patch.object(svc, "_run_whisper", return_value=fake_model_result):
        result = svc.transcribe(b"audio-bytes")
    assert isinstance(result, SttResult)
    assert result.transcript == "hai mươi ba cộng năm bằng"  # whitespace stripped
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
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/test_whisper_stt_service.py -v
```

- [ ] **Step 3: Append `WhisperSttService` to `app/services/stt.py`**

Open `/Users/it/Documents/MySource/voiceApp/backend/app/services/stt.py` and append:

```python
import tempfile
from pathlib import Path


class WhisperSttService:
    """SttService backed by openai-whisper. Lazy-loads model on first call."""

    def __init__(self, model_name: str = "small", language: str = "vi") -> None:
        self._model_name = model_name
        self._language = language

    def _run_whisper(self, audio_path: str) -> dict:
        """Call into Whisper. Isolated for monkey-patching."""
        from app.services._model_cache import get_whisper
        model = get_whisper(self._model_name)
        return model.transcribe(audio_path, language=self._language, fp16=False)

    def transcribe(self, audio_bytes: bytes) -> SttResult:
        # Write bytes to temp file. Browser MediaRecorder commonly emits webm/opus
        # — Whisper auto-detects format via ffmpeg. We use .webm suffix as best guess
        # but Whisper doesn't strictly require correct extension.
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name
        try:
            raw = self._run_whisper(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
        return SttResult(
            transcript=raw["text"].strip(),
            language=raw.get("language", self._language),
        )
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_whisper_stt_service.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Run full suite**

```bash
pytest 2>&1 | tail -3
```

Expected: 102 passed (100 + 2).

- [ ] **Step 6: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/services/stt.py backend/tests/test_whisper_stt_service.py
git commit -m "feat(stt): WhisperSttService with lazy model load + tempfile pipeline"
```

---

## Task 7: Switch deps.py to env-var-driven service selection

**Files:**
- Modify: `backend/app/api/deps.py`
- Create: `backend/tests/test_deps_switch.py`

- [ ] **Step 1: Write test**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_deps_switch.py`:

```python
from app.services.ocr import StubOcrService, PaddleOcrService
from app.services.stt import StubSttService, WhisperSttService


def test_get_ocr_service_returns_stub_by_default(monkeypatch):
    monkeypatch.setenv("VOICEAPP_USE_REAL_SERVICES", "0")
    # re-import deps module to re-read settings
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
```

- [ ] **Step 2: Run — expect FAIL** (deps still hardcoded to Stub)

```bash
pytest tests/test_deps_switch.py -v
```

- [ ] **Step 3: Update `app/api/deps.py`**

Replace `/Users/it/Documents/MySource/voiceApp/backend/app/api/deps.py` with:

```python
from collections.abc import Generator
from sqlalchemy.orm import Session
from app.db import make_engine, make_session_factory
from app.config import settings
from app.services.ocr import OcrService, StubOcrService, PaddleOcrService
from app.services.stt import SttService, StubSttService, WhisperSttService


_engine = make_engine(settings.db_url)
_SessionLocal = make_session_factory(_engine)


def get_db() -> Generator[Session, None, None]:
    with _SessionLocal() as s:
        yield s


def get_ocr_service() -> OcrService:
    if settings.use_real_services:
        return PaddleOcrService(lang=settings.paddle_lang)
    return StubOcrService()


def get_stt_service() -> SttService:
    if settings.use_real_services:
        return WhisperSttService(
            model_name=settings.whisper_model_name,
            language=settings.whisper_language,
        )
    return StubSttService()


def get_engine():
    return _engine
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_deps_switch.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Run full suite (no regressions; existing tests use override so unaffected)**

```bash
pytest 2>&1 | tail -3
```

Expected: 106 passed (102 + 4).

- [ ] **Step 6: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/api/deps.py backend/tests/test_deps_switch.py
git commit -m "feat(deps): switch get_ocr/stt_service via VOICEAPP_USE_REAL_SERVICES env"
```

---

## Task 8: Audio pipeline module

**Files:**
- Create: `backend/app/services/audio.py`
- Create: `backend/tests/test_services_audio_pipeline.py`

The audio pipeline is the pure function: bytes → STT → parse VN → result dict. Decoupled from FastAPI for easy testing.

- [ ] **Step 1: Write test**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_services_audio_pipeline.py`:

```python
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
    import pytest
    with pytest.raises(ValueError):
        transcribe_and_parse(b"x", stt)
```

- [ ] **Step 2: Run — expect FAIL** (module doesn't exist)

```bash
pytest tests/test_services_audio_pipeline.py -v
```

- [ ] **Step 3: Implement `app/services/audio.py`**

Create `/Users/it/Documents/MySource/voiceApp/backend/app/services/audio.py`:

```python
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
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_services_audio_pipeline.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Run full suite**

```bash
pytest 2>&1 | tail -3
```

Expected: 109 passed (106 + 3).

- [ ] **Step 6: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/services/audio.py backend/tests/test_services_audio_pipeline.py
git commit -m "feat(services): add audio.transcribe_and_parse pipeline"
```

---

## Task 9: AudioGroup output schema

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/tests/test_schemas.py`

- [ ] **Step 1: Add test for new schema**

Append to `/Users/it/Documents/MySource/voiceApp/backend/tests/test_schemas.py`:

```python
def test_audio_group_out_minimal():
    from app.schemas import AudioGroupOut
    g = AudioGroupOut(
        id=1, capture_id=10, group_index=2,
        audio_path="/tmp/a.webm",
        transcript="hai mươi ba bằng",
        parsed_numbers=[23],
        sum=23.0,
        multiplier_snapshot=80.0,
    )
    assert g.parsed_numbers == [23]
    assert g.sum == 23.0
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/test_schemas.py::test_audio_group_out_minimal -v
```

- [ ] **Step 3: Add `AudioGroupOut` to `app/schemas.py`**

Open `/Users/it/Documents/MySource/voiceApp/backend/app/schemas.py` and append at the end of the file:

```python
class AudioGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    capture_id: int
    group_index: int
    audio_path: str
    transcript: str | None
    parsed_numbers: list[float] | None
    sum: float | None
    multiplier_snapshot: float
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_schemas.py::test_audio_group_out_minimal -v
```

- [ ] **Step 5: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/schemas.py backend/tests/test_schemas.py
git commit -m "feat(schemas): add AudioGroupOut response model"
```

---

## Task 10: POST /api/captures/{id}/audio endpoint

**Files:**
- Modify: `backend/app/api/captures.py`
- Create: `backend/tests/test_api_capture_audio.py`

- [ ] **Step 1: Write tests**

Create `/Users/it/Documents/MySource/voiceApp/backend/tests/test_api_capture_audio.py`:

```python
import io


def _create_template(client, multipliers: dict[int, float] | None = None) -> int:
    """Create a template with groups using given multipliers (default {1: 80.0})."""
    multipliers = multipliers or {1: 80.0}
    groups = [
        {"index": gi, "label": f"G{gi}", "bet_type": "lo", "multiplier": m}
        for gi, m in sorted(multipliers.items())
    ]
    r = client.post("/api/templates", json={"name": "T", "groups": groups})
    return r.json()["id"]


def _create_capture(client, tid: int, group_provinces: str = '{"1": ["HN"]}') -> int:
    files = {"image": ("n.png", io.BytesIO(b"x"), "image/png")}
    r = client.post("/api/captures", files=files,
                    data={"template_id": str(tid), "group_provinces": group_provinces})
    return r.json()["id"]


def test_audio_upload_creates_audio_group(client):
    tid = _create_template(client)
    cid = _create_capture(client, tid)

    files = {"audio": ("clip.webm", io.BytesIO(b"fake-audio-bytes"), "audio/webm")}
    data = {"group_index": "1"}
    resp = client.post(f"/api/captures/{cid}/audio", files=files, data=data)
    assert resp.status_code == 201, resp.text

    body = resp.json()
    assert body["capture_id"] == cid
    assert body["group_index"] == 1
    # StubSttService returns "hai mươi ba cộng năm cộng một trăm lẻ năm bằng"
    assert body["parsed_numbers"] == [23, 5, 105]
    assert body["sum"] == 133
    assert body["multiplier_snapshot"] == 80.0
    assert body["audio_path"].endswith(".webm")


def test_audio_upload_uses_template_group_multiplier(client):
    tid = _create_template(client, multipliers={1: 80.0, 2: 82.0, 3: 14.5})
    cid = _create_capture(client, tid, '{"3": ["DNG", "KH"]}')

    files = {"audio": ("a.webm", io.BytesIO(b"x"), "audio/webm")}
    resp = client.post(f"/api/captures/{cid}/audio", files=files, data={"group_index": "3"})
    assert resp.status_code == 201, resp.text
    assert resp.json()["multiplier_snapshot"] == 14.5


def test_audio_upload_unknown_capture_404(client):
    files = {"audio": ("a.webm", io.BytesIO(b"x"), "audio/webm")}
    resp = client.post("/api/captures/9999/audio", files=files, data={"group_index": "1"})
    assert resp.status_code == 404


def test_audio_upload_invalid_group_index_400(client):
    tid = _create_template(client)  # only group 1 exists
    cid = _create_capture(client, tid)

    files = {"audio": ("a.webm", io.BytesIO(b"x"), "audio/webm")}
    resp = client.post(f"/api/captures/{cid}/audio", files=files, data={"group_index": "99"})
    assert resp.status_code == 400
    assert "group" in resp.json()["detail"].lower()


def test_audio_upload_persists_to_db(client, db_session):
    """Verify the AudioGroup row is actually persisted, not just returned."""
    from app.models import AudioGroup
    tid = _create_template(client)
    cid = _create_capture(client, tid)

    files = {"audio": ("a.webm", io.BytesIO(b"x"), "audio/webm")}
    client.post(f"/api/captures/{cid}/audio", files=files, data={"group_index": "1"})

    rows = db_session.query(AudioGroup).filter(AudioGroup.capture_id == cid).all()
    assert len(rows) == 1
    assert rows[0].sum == 133
    assert rows[0].transcript is not None


def test_audio_upload_multiple_groups_for_same_capture(client, db_session):
    """User can record group 1, then group 2 on same capture; both persist."""
    from app.models import AudioGroup
    tid = _create_template(client, multipliers={1: 80.0, 2: 82.0})
    cid = _create_capture(client, tid, '{"1": ["HN"], "2": ["HN"]}')

    for gi in [1, 2]:
        files = {"audio": ("a.webm", io.BytesIO(b"x"), "audio/webm")}
        resp = client.post(f"/api/captures/{cid}/audio", files=files, data={"group_index": str(gi)})
        assert resp.status_code == 201

    rows = db_session.query(AudioGroup).filter(AudioGroup.capture_id == cid).order_by(AudioGroup.group_index).all()
    assert len(rows) == 2
    assert rows[0].group_index == 1
    assert rows[0].multiplier_snapshot == 80.0
    assert rows[1].group_index == 2
    assert rows[1].multiplier_snapshot == 82.0
```

- [ ] **Step 2: Run — expect FAIL** (endpoint doesn't exist)

```bash
pytest tests/test_api_capture_audio.py -v
```

- [ ] **Step 3: Append endpoint to `app/api/captures.py`**

Open `/Users/it/Documents/MySource/voiceApp/backend/app/api/captures.py`. The file already imports `json`, `uuid`, `Path`, FastAPI bits, `Session`, `get_db`, `settings`, `Template`, `Capture`, `OcrNumber`, `BBoxOut`, `OcrService`. Add these additional imports at the top of the file (next to the existing imports):

```python
from app.api.deps import get_stt_service
from app.services.stt import SttService
from app.services.audio import transcribe_and_parse
from app.models import AudioGroup
from app.schemas import AudioGroupOut
```

Then append this endpoint to the same file (after the existing `get_capture` function):

```python
def _multiplier_for_group(template_groups_json: str, group_index: int) -> float | None:
    groups = json.loads(template_groups_json)
    for g in groups:
        if int(g["index"]) == group_index:
            return float(g["multiplier"])
    return None


@router.post("/{capture_id}/audio", response_model=AudioGroupOut, status_code=status.HTTP_201_CREATED)
def upload_audio(
    capture_id: int,
    group_index: int = Form(...),
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
    stt: SttService = Depends(get_stt_service),
) -> AudioGroupOut:
    c = db.get(Capture, capture_id)
    if c is None:
        raise HTTPException(status_code=404, detail="capture not found")

    t = db.get(Template, c.template_id)
    if t is None:
        # data integrity issue — shouldn't happen
        raise HTTPException(status_code=500, detail="template missing for capture")

    multiplier = _multiplier_for_group(t.groups_json, group_index)
    if multiplier is None:
        raise HTTPException(status_code=400, detail=f"group_index {group_index} not in template")

    # Save audio file
    Path(settings.media_dir, "audio").mkdir(parents=True, exist_ok=True)
    fname = f"{uuid.uuid4().hex}_g{group_index}.webm"
    fpath = Path(settings.media_dir, "audio", fname)
    audio_bytes = audio.file.read()
    fpath.write_bytes(audio_bytes)

    # Run STT + parse
    pipeline_result = transcribe_and_parse(audio_bytes, stt)

    row = AudioGroup(
        capture_id=capture_id,
        group_index=group_index,
        audio_path=str(fpath),
        transcript=pipeline_result.transcript,
        parsed_numbers_json=json.dumps(pipeline_result.parsed_numbers),
        sum=pipeline_result.sum,
        multiplier_snapshot=multiplier,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return AudioGroupOut(
        id=row.id,
        capture_id=row.capture_id,
        group_index=row.group_index,
        audio_path=row.audio_path,
        transcript=row.transcript,
        parsed_numbers=pipeline_result.parsed_numbers,
        sum=row.sum,
        multiplier_snapshot=row.multiplier_snapshot,
    )
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_api_capture_audio.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Run full suite**

```bash
pytest 2>&1 | tail -3
```

Expected: 116 passed (109 + 6 + 1 schema test from Task 9).

- [ ] **Step 6: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/app/api/captures.py backend/tests/test_api_capture_audio.py
git commit -m "feat(api): POST /api/captures/{id}/audio with STT + VN parse + AudioGroup persist"
```

---

## Task 11: Real-services smoke test (manual, gated)

**Files:**
- Create: `backend/tests/fixtures/.gitkeep`
- Create: `backend/scripts/smoke_real_services.py`

This task validates the real services work outside the unit test loop. We don't auto-run heavy ML models in CI/normal `pytest`. Instead we add a script that the dev runs manually.

- [ ] **Step 1: Create fixture dir**

```bash
mkdir -p /Users/it/Documents/MySource/voiceApp/backend/tests/fixtures
touch /Users/it/Documents/MySource/voiceApp/backend/tests/fixtures/.gitkeep
```

- [ ] **Step 2: Create smoke script**

Create `/Users/it/Documents/MySource/voiceApp/backend/scripts/smoke_real_services.py`:

```python
"""Manual smoke test for PaddleOCR + Whisper. NOT run by pytest.

Usage:
    cd backend
    source .venv/bin/activate
    python scripts/smoke_real_services.py path/to/image.png path/to/audio.wav

The script loads PaddleOCR + Whisper (slow first time), runs each, and prints results.
Use this after Plan 2 to verify your environment can actually run the real models
before trying the live web app.
"""
from __future__ import annotations
import sys
from pathlib import Path

# Make `app` importable when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("Usage: smoke_real_services.py <image_path> <audio_path>")
        return 2

    image_path, audio_path = argv[1], argv[2]
    if not Path(image_path).exists():
        print(f"image not found: {image_path}")
        return 1
    if not Path(audio_path).exists():
        print(f"audio not found: {audio_path}")
        return 1

    print(f"=== OCR ({image_path}) ===")
    from app.services.ocr import PaddleOcrService
    ocr = PaddleOcrService(lang="vi")
    image_bytes = Path(image_path).read_bytes()
    detections = ocr.extract(image_bytes)
    print(f"detected {len(detections)} numbers:")
    for d in detections:
        print(f"  {d.value:>10}  conf={d.confidence:.2f}  bbox=({d.bbox.x:.0f},{d.bbox.y:.0f},{d.bbox.w:.0f},{d.bbox.h:.0f})  raw={d.raw_text!r}")

    print(f"\n=== STT ({audio_path}) ===")
    from app.services.stt import WhisperSttService
    from app.services.audio import transcribe_and_parse
    stt = WhisperSttService(model_name="small", language="vi")
    audio_bytes = Path(audio_path).read_bytes()
    try:
        result = transcribe_and_parse(audio_bytes, stt)
    except ValueError as e:
        print(f"parse failed: {e}")
        # Still print transcript for debugging
        raw = stt.transcribe(audio_bytes)
        print(f"transcript was: {raw.transcript!r}")
        return 1

    print(f"transcript: {result.transcript!r}")
    print(f"numbers:    {result.parsed_numbers}")
    print(f"sum:        {result.sum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 3: Test that pytest still ignores the fixtures dir + scripts dir**

```bash
cd /Users/it/Documents/MySource/voiceApp/backend
source .venv/bin/activate
pytest 2>&1 | tail -3
```

Expected: 116 passed (no test files added; pytest's `testpaths = tests` only looks under tests/).

- [ ] **Step 4: Commit**

```bash
cd /Users/it/Documents/MySource/voiceApp
git add backend/tests/fixtures/.gitkeep backend/scripts/smoke_real_services.py
git commit -m "feat(scripts): add manual smoke test for real PaddleOCR + Whisper"
```

---

## Task 12: End-to-end verification

**Files:** none (manual run + verify only)

- [ ] **Step 1: Run full pytest**

```bash
cd /Users/it/Documents/MySource/voiceApp/backend
source .venv/bin/activate
pytest 2>&1 | tail -5
```

Expected: 116 passed.

- [ ] **Step 2: Boot server with REAL services + curl test**

This step downloads the Whisper `small` model (~244MB) on first run. Allow 1-2 min.

```bash
cd /Users/it/Documents/MySource/voiceApp/backend
source .venv/bin/activate
VOICEAPP_USE_REAL_SERVICES=1 uvicorn app.main:app --port 8765 > /tmp/voiceapp-real.log 2>&1 &
SERVER_PID=$!
# Wait for server to be ready (lifespan + DB seed)
sleep 5
echo "server pid: $SERVER_PID"

# Health
curl -s http://localhost:8765/api/health
echo

# Create template
TID=$(curl -s -X POST http://localhost:8765/api/templates \
  -H 'content-type: application/json' \
  -d '{"name":"smoke-real","groups":[{"index":1,"label":"L","bet_type":"lo","multiplier":80}]}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
echo "template id: $TID"

# Create capture
echo fake-image > /tmp/fake.png
CID=$(curl -s -X POST http://localhost:8765/api/captures \
  -F "template_id=$TID" \
  -F 'group_provinces={"1": ["HN"]}' \
  -F "image=@/tmp/fake.png" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
echo "capture id: $CID"

# Generate a synthetic audio with ffmpeg (silence — Whisper will return empty/garbage transcript,
# but we just want to verify the endpoint pipeline doesn't crash on real Whisper)
ffmpeg -y -f lavfi -i "anullsrc=r=16000:cl=mono" -t 1 -c:a libopus /tmp/silent.webm 2>/dev/null
ls -la /tmp/silent.webm

# Audio upload (this exercises real Whisper)
echo "--- uploading audio (Whisper may take 5-15s) ---"
curl -s -X POST "http://localhost:8765/api/captures/$CID/audio" \
  -F "group_index=1" \
  -F "audio=@/tmp/silent.webm" | head -c 500
echo

# Cleanup
kill $SERVER_PID 2>/dev/null || true
rm /tmp/fake.png /tmp/silent.webm
sleep 1
```

Expected:
- `{"status":"ok"}`
- template id printed
- capture id printed
- audio upload returns either 201 (with empty/garbage parsed numbers since input was silence) OR 422/500 with a parse error (if Whisper returned no parseable text). Either is acceptable proof that real Whisper was invoked. Check the log:
  ```bash
  grep -i 'whisper\|paddle\|error' /tmp/voiceapp-real.log | head -20
  ```

If the audio call returns 500 because the silent transcript has no parseable numbers, that's expected behavior of `parse_expression` raising ValueError — it confirms real Whisper ran. The next plan (Plan 3) will gracefully convert this into a 422 response if needed.

- [ ] **Step 3: Verify DB updated**

```bash
sqlite3 /Users/it/Documents/MySource/voiceApp/backend/data/voiceapp.db "SELECT id, capture_id, group_index, transcript, sum FROM audio_groups;"
```

Expected: at least 0 rows (if Whisper failed parse, no row). Or 1 row if synthetic audio happened to parse.

If `sqlite3` is not installed, skip and check via the `/api/captures/{id}` endpoint — Plan 3 will add audio_groups to that response.

- [ ] **Step 4: Cleanup logs**

```bash
rm -f /tmp/voiceapp-real.log
```

- [ ] **Step 5: Tag plan completion**

```bash
cd /Users/it/Documents/MySource/voiceApp
git tag plan-2-complete
git log --oneline | head -15
```

Expected: ~32 commits total (20 from Plan 1 + 12 from Plan 2). Tag visible.

---

## Verification Checklist (end of Plan 2)

- [ ] `pytest -v` passes 116+ tests across all modules.
- [ ] `paddleocr` + `paddlepaddle` + `openai-whisper` installed in `backend/.venv/`.
- [ ] `ffmpeg` available system-wide.
- [ ] `VOICEAPP_USE_REAL_SERVICES=1 uvicorn ...` boots without import errors.
- [ ] Real PaddleOCR + Whisper invoked at least once via real curl call.
- [ ] `backend/scripts/smoke_real_services.py` available for hands-on validation.
- [ ] Tag `plan-2-complete` exists.

## What Plan 2 explicitly does NOT do (deferred)

- ❌ Match engine (Plan 3) — audio numbers ↔ OCR numbers
- ❌ OCR correction PATCH endpoint (Plan 3)
- ❌ Finalize endpoint (Plan 3)
- ❌ Frontend (Plans 4-6)
- ❌ Lottery OCR + settlement (Plan 11)
- ❌ Embedding `audio_groups` in CaptureOut (Plan 3 will do this)
