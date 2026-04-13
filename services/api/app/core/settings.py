from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Travel Project API"
    app_env: str = "development"
    app_base_url: str = "http://127.0.0.1:3000"
    api_base_url: str = "http://127.0.0.1:8000"
    local_storage_root: str = "./storage/local"
    cors_origins: str = "http://127.0.0.1:3000,http://localhost:3000"

    copilot_default_model_alias: str = "ggl2"
    gemini_fast_model: str = "gemini-2.5-flash"

    storage_backend: str = "s3"
    queue_backend: str = "sqs"


@lru_cache
def get_settings() -> Settings:
    return Settings()
