from __future__ import annotations

from enum import Enum
from functools import lru_cache
from typing import Annotated

from pydantic import AnyHttpUrl, Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class LogFormat(str, Enum):
    JSON = "json"
    CONSOLE = "console"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Application ─────────────────────────────────────────────────────────
    APP_NAME: str = "Astra"
    APP_ENV: AppEnvironment = AppEnvironment.DEVELOPMENT
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = Field(..., min_length=32)
    ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1"]

    # ─── API ─────────────────────────────────────────────────────────────────
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [h.strip() for h in v.split(",")]
        return v

    # ─── PostgreSQL ───────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://astra:astra_secret@localhost:5432/astra"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600
    DATABASE_ECHO: bool = False

    # ─── Redis ───────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50

    # ─── JWT Auth ─────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ─── Security ─────────────────────────────────────────────────────────────
    BCRYPT_ROUNDS: int = 12
    RATE_LIMIT_PER_MINUTE: int = 60

    # ─── Logging ─────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: LogFormat = LogFormat.JSON
    LOG_FILE: str | None = None

    # ─── AI Model Keys ───────────────────────────────────────────────────────
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    GOOGLE_API_KEY: str | None = None
    DEEPSEEK_API_KEY: str | None = None

    # ─── External Services ───────────────────────────────────────────────────
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str | None = None

    SENTRY_DSN: str | None = None

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == AppEnvironment.PRODUCTION

    @property
    def is_testing(self) -> bool:
        return self.APP_ENV == AppEnvironment.TESTING

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == AppEnvironment.DEVELOPMENT


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
