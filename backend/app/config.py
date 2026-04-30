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
