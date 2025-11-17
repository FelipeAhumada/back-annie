"""
Centralized configuration management.

Follows Layer 5 rules:
- All secrets (DB URLs, JWT keys, API keys, third-party credentials) MUST come from
  environment variables or a secure secret store (never hardcoded)
- Centralize configuration in this module
- Do not spread os.getenv calls all over the codebase
- Do not log secrets or environment values
"""
from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # --- Postgres ---
    PG_HOST: str = Field(..., description="PostgreSQL host")
    PG_PORT: int = Field(default=5432, description="PostgreSQL port")
    PG_DB: str = Field(..., description="PostgreSQL database name")
    PG_USER: str = Field(..., description="PostgreSQL user")
    PG_PASSWORD: str = Field(..., description="PostgreSQL password")
    PG_SSLMODE: str = Field(default="require", description="PostgreSQL SSL mode (require/disable)")
    PG_SCHEMA: str = Field(default="annie,public", description="PostgreSQL schema")
    
    # --- JWT ---
    JWT_SECRET: str = Field(..., description="JWT signing secret key")
    JWT_EXP_MIN: int = Field(default=120, description="JWT expiration in minutes")
    
    # --- Redis/Valkey ---
    REDIS_HOST: str = Field(default="redis", description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_PASSWORD: str | None = Field(default=None, description="Redis password")
    REDIS_SSL: str = Field(default="false", description="Redis SSL enabled (true/false)")
    
    # --- Spaces / S3 ---
    DO_REGION: str = Field(..., description="DigitalOcean Spaces region")
    DO_BUCKET: str = Field(..., description="DigitalOcean Spaces bucket name")
    DO_ACCESS_KEY: str = Field(..., description="DigitalOcean Spaces access key")
    DO_SECRET_KEY: str = Field(..., description="DigitalOcean Spaces secret key")
    DO_SPACES_ENDPOINT: str | None = Field(default=None, description="DigitalOcean Spaces endpoint")
    SPACES_PUBLIC_BASE: str | None = Field(default=None, description="Public base URL for Spaces")
    
    # --- LLM API Keys ---
    OPENAI_API_KEY: str | None = Field(default=None, description="OpenAI API key")
    GEMINI_API_KEY: str | None = Field(default=None, description="Google Gemini API key")
    GROK_API_KEY: str | None = Field(default=None, description="Grok API key")
    EMBED_MODEL: str = Field(default="text-embedding-3-small", description="Embedding model name")
    
    # --- CORS ---
    CORS_ORIGINS: str = Field(default="*", description="CORS allowed origins (comma-separated)")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
