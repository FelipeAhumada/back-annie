# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # --- Postgres ---
    PG_HOST: str
    PG_PORT: int = 5432
    PG_DB: str
    PG_USER: str
    PG_PASSWORD: str
    PG_SSLMODE: str = "require"  # prod= require; local= disable
    PG_SCHEMA: str = "annie,public"  # 👈 NEW: esquema por defecto
    # --- JWT ---
    JWT_SECRET: str
    JWT_EXP_MIN: int = 120

    # --- Redis ---
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None

    # --- Spaces / S3 ---
    DO_REGION: str
    DO_BUCKET: str
    DO_ACCESS_KEY: str
    DO_SECRET_KEY: str
    DO_SPACES_ENDPOINT: str | None = None  # ej: http://minio:9000

    # --- CORS ---
    CORS_ORIGINS: str = "*"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

settings = Settings()
