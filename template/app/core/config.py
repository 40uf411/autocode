from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "CleanAuthAPI"
    debug: bool = False
    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    postgres_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/cleanauth"
    jwt_secret_key: str = "change-this-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    cache_ttl_seconds: int = 30
    cache_url: str = "redis://cache:6379/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
