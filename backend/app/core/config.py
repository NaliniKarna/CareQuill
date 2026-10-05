"""
Central application configuration.

All configuration is read from environment variables (see `.env.example` at
the repo root). Nothing here should be hardcoded: model names, credentials,
feature flags and external service settings all come from the environment so
that behaviour can change per-deployment without code changes.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- General ---
    environment: Literal["development", "test", "production"] = "development"
    project_name: str = "MedQueue AI"
    api_v1_prefix: str = "/api/v1"

    # --- Database ---
    database_url: str = (
        "postgresql+asyncpg://medqueue:medqueue_dev_pw@localhost:5432/medqueue_ai"
    )
    test_database_url: str | None = None
    db_echo: bool = False

    # --- Auth / JWT ---
    jwt_secret_key: str = "change-this-to-a-random-64-char-hex-secret-before-deploying"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # --- CORS ---
    cors_origins: str = "http://localhost:3000"

    # --- Server ---
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    log_level: str = "INFO"

    # --- Storage ---
    storage_backend: Literal["local", "s3"] = "local"
    storage_local_path: str = "./storage/medical_documents"
    max_upload_size_mb: int = 15
    allowed_upload_extensions: str = ".pdf,.png,.jpg,.jpeg"

    s3_bucket_name: str | None = None
    s3_region: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_endpoint_url: str | None = None

    # --- Email ---
    email_backend: Literal["smtp", "sendgrid", "mailgun", "console"] = "console"
    email_from_address: str = "no-reply@medqueue.ai"
    email_from_name: str = "MedQueue AI"

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = False

    sendgrid_api_key: str | None = None
    mailgun_api_key: str | None = None
    mailgun_domain: str | None = None

    # --- AI ---
    ai_enabled: bool = False
    ai_provider: Literal["ollama", "none"] = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = Field(default="llama3.2")
    ai_prompt_version: str = "v1"

    # --- OCR ---
    ocr_enabled: bool = False
    ocr_engine: Literal["easyocr", "paddleocr", "tesseract", "none"] = "tesseract"

    # --- Frontend origin used by generated links (password reset, etc.) ---
    frontend_base_url: str = "http://localhost:3000"

    @field_validator("cors_origins")
    @classmethod
    def _validate_cors(cls, v: str) -> str:
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allowed_upload_extensions_list(self) -> list[str]:
        return [
            ext.strip().lower()
            for ext in self.allowed_upload_extensions.split(",")
            if ext.strip()
        ]

    @property
    def is_test(self) -> bool:
        return self.environment == "test"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
