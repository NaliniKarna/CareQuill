"""
Central application configuration.

All configuration is read from environment variables (see `.env.example` at
the repo root). Nothing here should be hardcoded: model names, credentials,
feature flags and external service settings all come from the environment so
that behaviour can change per-deployment without code changes.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- General ---
    environment: Literal["development", "test", "production"] = "development"
    project_name: str = "CareQuill"
    api_v1_prefix: str = "/api/v1"

    # --- Database ---
    database_url: str = (
        "postgresql+asyncpg://medqueue:medqueue_dev_pw@localhost:5432/medqueue_ai"
    )
    test_database_url: str | None = None
    db_echo: bool = False
    # Connection pool. SQLAlchemy's defaults (5 + 10 overflow) are fine for
    # one worker; with several gunicorn workers each gets its own pool, so
    # keep (pool_size + max_overflow) * workers below Postgres' max_connections.
    db_pool_size: int = 10
    db_max_overflow: int = 10
    db_pool_recycle_seconds: int = 1800

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
    email_from_name: str = "CareQuill"

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
    # A summary prompt (verified snapshot + timeline + extractions) is far
    # larger than Ollama's default 2048-token context; when the context is
    # too small Ollama SILENTLY truncates the start of the prompt (the
    # safety rules!) and the model answers with invalid JSON. 8192 keeps the
    # whole prompt intact for llama3.2-class models.
    ollama_num_ctx: int = 8192
    ollama_temperature: float = 0.1
    # Generation on a CPU-only machine (a typical student laptop) can take
    # minutes for the first call while the model loads into memory.
    ollama_timeout_seconds: float = 300.0
    # Keep the model resident between calls so only the first request pays
    # the load cost.
    ollama_keep_alive: str = "30m"
    # Document intelligence (all optional; the regex extractor always runs
    # and is the fallback whenever AI is off or fails):
    ai_document_extraction_enabled: bool = True
    ai_document_explain_enabled: bool = True
    # Vision model used ONLY to describe what kind of image an upload is
    # (modality, body region, quality, visible text). It never reports
    # findings. Needs a multimodal model pulled in Ollama, e.g.
    # `ollama pull llama3.2-vision` or `ollama pull llava`.
    ai_vision_enabled: bool = False
    ollama_vision_model: str = "llama3.2-vision"

    # --- OCR ---
    ocr_enabled: bool = False
    ocr_engine: Literal["easyocr", "paddleocr", "tesseract", "none"] = "tesseract"
    # Tesseract language pack(s), "+"-joined (e.g. "eng+nep"). Packs must be
    # installed in the image (see backend/Dockerfile).
    ocr_languages: str = "eng"
    # Uploads whose OCR yields fewer words than this are reported as "no
    # readable text" instead of "completed" with an empty extraction.
    ocr_min_words: int = 5
    # Hard cap per OCR call so one pathological scan can't hold a worker.
    ocr_timeout_seconds: int = 60
    # Max PDF pages OCR'd (scanned PDFs only) -- bounds worst-case CPU.
    ocr_max_pdf_pages: int = 20

    # --- Abuse protection ---
    rate_limit_enabled: bool = True
    # Per client IP, per route group, sliding window.
    auth_rate_limit_attempts: int = 10
    auth_rate_limit_window_seconds: int = 60
    ai_rate_limit_attempts: int = 10
    ai_rate_limit_window_seconds: int = 60
    upload_rate_limit_attempts: int = 30
    upload_rate_limit_window_seconds: int = 60
    # Public QR/link access to a shared report (no login), per client IP.
    shared_link_rate_limit_attempts: int = 30
    shared_link_rate_limit_window_seconds: int = 60

    # --- Report sharing ---
    # Email providers commonly reject messages over ~25 MB; keep the PDF plus
    # attached documents under this so the doctor actually receives them.
    max_email_attachments_mb: int = 20
    # Longest a patient can keep a QR/link share open.
    share_link_max_hours: int = 720

    # --- Family circle ---
    family_max_members: int = 25
    family_invite_valid_days: int = 7

    # --- Observability ---
    slow_request_threshold_ms: int = 1000

    # --- Frontend origin used by generated links (password reset, etc.) ---
    frontend_base_url: str = "http://localhost:3000"

    @field_validator("cors_origins")
    @classmethod
    def _validate_cors(cls, v: str) -> str:
        return v

    @model_validator(mode="after")
    def _refuse_insecure_production_config(self) -> "Settings":
        """Fail fast at boot instead of silently running a production
        deployment with development defaults (a well-known default JWT
        secret would let anyone forge tokens for any patient)."""
        if self.environment != "production":
            return self

        problems: list[str] = []
        if (
            self.jwt_secret_key.startswith("change-this")
            or len(self.jwt_secret_key) < 32
        ):
            problems.append("JWT_SECRET_KEY must be a random value of at least 32 characters")
        if "medqueue_dev_pw" in self.database_url:
            problems.append("DATABASE_URL still uses the development database password")
        if any(o.strip() in ("*", "") for o in self.cors_origins.split(",")):
            problems.append("CORS_ORIGINS must list explicit origins (no '*')")
        if self.email_backend == "console":
            problems.append(
                "EMAIL_BACKEND=console only prints emails to the log; "
                "configure smtp, sendgrid or mailgun so verification, "
                "password-reset and share-with-doctor emails are really sent"
            )
        if problems:
            raise ValueError(
                "Refusing to start with ENVIRONMENT=production: " + "; ".join(problems) + "."
            )
        return self

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
