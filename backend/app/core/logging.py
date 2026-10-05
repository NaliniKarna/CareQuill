"""
Application-wide logging configuration.

Rules:
 - Never log passwords, JWTs, refresh tokens, or medical data.
 - Structured (JSON) logs in production-like environments so they can be
   shipped to a log aggregator; human-readable logs in development.
"""
import contextvars
import logging
import sys
import uuid

from app.core.config import settings

_SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "jwt",
}

# Per-request correlation id. Set/reset by the request-id middleware in
# app.main around each request; read here by RequestIdFilter so every log
# record emitted while handling a request carries the same id, without
# threading it through every function signature.
_request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


def get_request_id() -> str | None:
    return _request_id_var.get()


def set_request_id(request_id: str | None) -> contextvars.Token:
    return _request_id_var.set(request_id)


def reset_request_id(token: contextvars.Token) -> None:
    _request_id_var.reset(token)


def new_request_id() -> str:
    return uuid.uuid4().hex


class RedactSensitiveFilter(logging.Filter):
    """Best-effort redaction of common sensitive field names in log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, dict):
            record.args = {
                k: ("***REDACTED***" if k.lower() in _SENSITIVE_KEYS else v)
                for k, v in record.args.items()
            }
        return True


class RequestIdFilter(logging.Filter):
    """Injects the current request's correlation id (see
    `app.main`'s request-id middleware) into every log record as
    `record.request_id`, defaulting to "-" outside a request (startup/
    shutdown, background tasks)."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        return True


def configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | request_id=%(request_id)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setFormatter(formatter)
    handler.addFilter(RedactSensitiveFilter())
    handler.addFilter(RequestIdFilter())

    root.handlers = [handler]

    # Quiet noisy third-party loggers.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.db_echo else logging.WARNING
    )


logger = logging.getLogger("medqueue")
