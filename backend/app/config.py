from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    demo_mode: bool = True
    database_url: str = "sqlite:///./pivotpilot.db"
    frontend_origins: list[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]
    supabase_url: str = ""
    supabase_anon_key: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    max_upload_bytes: int = 5_000_000
    max_scan_bytes: int = 1_000_000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("frontend_origins", mode="before")
    @classmethod
    def split_frontend_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
