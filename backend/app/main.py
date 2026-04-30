from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.db import Base
from app.api.deps import _SessionLocal, _engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.media_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    from app import models  # noqa: F401  (populate metadata)
    Base.metadata.create_all(_engine)
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

    # Serve uploaded media (images + audio) — read-only
    Path(settings.media_dir).mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    from app.api.provinces import router as provinces_router
    app.include_router(provinces_router)

    from app.api.templates import router as templates_router
    app.include_router(templates_router)

    from app.api.captures import router as captures_router
    app.include_router(captures_router)

    return app


app = create_app()
