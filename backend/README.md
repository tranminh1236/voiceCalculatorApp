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
