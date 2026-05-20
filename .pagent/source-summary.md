# Source Summary

**Project type:** monorepo (python-fastapi + react-ts)
**Language(s):** Python 3.11 (backend), TypeScript / TSX (frontend)
**Entry point:** `backend/app/main.py` (FastAPI `app`), `frontend/src/main.tsx` (React)
**Test framework:** pytest (backend), vitest + @testing-library/react (frontend)
**Test command:** `cd backend && pytest -v` / `cd frontend && npm test`
**Build command:** `cd frontend && tsc && vite build`
**Run command:** `cd backend && uvicorn app.main:app --reload --port 8000` / `cd frontend && npm run dev`

## Cấu trúc thư mục

```
voiceApp/
├── backend/                  # FastAPI Python service (port 8000)
│   ├── app/
│   │   ├── main.py           # App factory, lifespan, CORS, router registration
│   │   ├── config.py         # Pydantic settings (media_dir, db_path, cors_origins)
│   │   ├── db.py             # SQLAlchemy engine + session factory
│   │   ├── models.py         # ORM models (Capture, Province, Template, …)
│   │   ├── schemas.py        # Pydantic request/response schemas
│   │   ├── seed.py           # Province seed data
│   │   ├── api/
│   │   │   ├── captures.py   # REST endpoints: CRUD + audio, OCR, risk, finalize
│   │   │   ├── provinces.py  # GET /api/provinces
│   │   │   ├── templates.py  # GET/POST /api/templates
│   │   │   └── deps.py       # DB session dependency injection
│   │   ├── domain/
│   │   │   └── enums.py      # Shared enums (status, recommendation, …)
│   │   └── services/
│   │       ├── audio.py      # Audio pipeline (record → STT → parse)
│   │       ├── matcher.py    # Match parsed numbers to lottery results
│   │       ├── ocr.py        # OCR dispatch (PaddleOCR / EasyOCR)
│   │       ├── parser_vn.py  # Vietnamese number/lottery ticket parser
│   │       ├── risk.py       # compute_risk() — per-entry payout/net/share
│   │       ├── stt.py        # Whisper STT wrapper
│   │       └── _model_cache.py # Lazy model loading cache
│   ├── tests/                # pytest test suite (unit + integration)
│   ├── data/                 # Lottery result fixtures / seed data
│   ├── scripts/              # Dev/utility scripts
│   ├── requirements.txt      # Runtime deps (FastAPI, SQLAlchemy, PaddleOCR, Whisper…)
│   └── requirements-dev.txt  # Dev deps (pytest, httpx, …)
├── frontend/                 # React 18 SPA (Vite, TypeScript, Tailwind)
│   ├── src/
│   │   ├── main.tsx          # React entry, ReactQueryClientProvider, router
│   │   ├── App.tsx           # Route definitions
│   │   ├── api/
│   │   │   ├── client.ts     # Axios instance (baseURL /api)
│   │   │   └── types.ts      # Shared TS types mirroring backend schemas
│   │   ├── hooks/            # React Query hooks (useCaptures, useCapture, useRecorder, …)
│   │   ├── pages/            # Route-level pages (NewCapture, CaptureDetail, History, Templates)
│   │   └── components/       # UI components (RiskPanel, AudioRecorder, OcrOverlay, …)
│   ├── public/               # Static assets
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── vitest.config.ts
└── docs/                     # Architecture / design docs
```

## Convention

- **Naming:** snake_case throughout Python; camelCase/PascalCase in TypeScript (components PascalCase, hooks `useXxx`, API fns camelCase)
- **Import style:** Backend uses absolute imports from `app.*`; frontend uses relative imports within `src/`
- **Module boundary:** Backend is layered — `api/` → `services/` → `domain/`; frontend separates `api/` (fetchers) from `hooks/` (React Query wrappers) from `components/` (UI)

## Domain

VoiceApp là công cụ ghi nhận và phân tích vé số thủ công có hỗ trợ giọng nói. Người dùng chụp ảnh hoặc ghi âm số vé, hệ thống OCR/STT trích xuất số, đối chiếu với kết quả xổ số, và tính toán rủi ro (payout/net/share) theo ngưỡng cấu hình. Mục tiêu: hỗ trợ đại lý vé số quản lý tờ vé và kiểm tra kết quả nhanh.

## Files quan trọng

- `backend/app/main.py` — App factory, lifespan (DB init + seed), router mounting
- `backend/app/services/risk.py` — Pure `compute_risk()` business logic, per-entry payout/net/share/recommendation
- `backend/app/services/audio.py` — Full audio pipeline: record → Whisper STT → parser → matcher
- `backend/app/services/ocr.py` — OCR engine dispatch (PaddleOCR primary, EasyOCR fallback)
- `backend/app/api/captures.py` — Core REST surface: upload, OCR, audio, finalize, risk endpoint
- `frontend/src/hooks/useCapture.ts` — Central capture state hook (React Query)
- `frontend/src/components/RiskPanel.tsx` — Collapsible risk report UI with threshold slider
- `frontend/src/pages/CaptureDetail.tsx` — Main capture workflow page
- `backend/tests/test_risk_calculator.py` — Risk logic unit tests
- `backend/tests/test_capture_flow_integration.py` — End-to-end capture flow integration test
