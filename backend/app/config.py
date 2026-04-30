from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parent.parent  # backend/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VOICEAPP_", env_file=".env", extra="ignore")

    db_path: str = str(BACKEND_ROOT / "data" / "voiceapp.db")
    media_dir: str = str(BACKEND_ROOT / "data" / "media")
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    use_real_services: bool = False
    ocr_backend: str = "easyocr"  # easyocr | paddle (easyocr default — much faster on Apple Silicon)
    whisper_model_name: str = "small"  # tiny | base | small | medium | large
    whisper_language: str = "vi"
    paddle_lang: str = "vi"

    @property
    def db_url(self) -> str:
        return f"sqlite:///{self.db_path}"


settings = Settings()
