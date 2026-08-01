"""Application configuration loaded from environment variables."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the WhatsApp Message Notification Router."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- API Keys & Auth ---
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    API_BEARER_TOKEN: str = "dev-token"

    # --- Database ---
    DATABASE_URL: str = "sqlite:///./messages.db"

    # --- Paths ---
    MEDIA_STORAGE_PATH: str = "./dataset/media"
    DATASET_PATH: str = "./dataset"

    # --- Routing ---
    USER_HANDLE: str = "@Rafay"

    # --- App ---
    APP_TITLE: str = "WhatsApp Message Notification Router"
    APP_VERSION: str = "1.0.0"
    LOG_LEVEL: str = "INFO"

    @property
    def dataset_dir(self) -> Path:
        return Path(self.DATASET_PATH).resolve()

    @property
    def media_dir(self) -> Path:
        return Path(self.MEDIA_STORAGE_PATH).resolve()


settings = Settings()
