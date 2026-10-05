"""
Application-level exceptions and the FastAPI exception handlers that turn
them into consistent JSON error responses.

Consistent error shape:
    {
        "error": {
            "code": "invalid_credentials",
            "message": "Human readable message safe to show the user",
            "details": null
        }
    }

Handlers never leak stack traces, SQL, or internal exception text to the
client; unexpected exceptions are logged server-side with full detail and
returned to the client as a generic 500 message.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("medqueue")


class AppError(Exception):
    """Base class for expected, handled application errors."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "app_error"

    def __init__(self, message: str, *, details: object | None = None) -> None:
        self.message = message
        self.details = details
        super().__init__(message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"


class ValidationAppError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "validation_error"


class AIGenerationError(AppError):
    """The configured AI provider failed to produce a usable result -- an
    unreachable/erroring provider, or output that still didn't validate as
    `StructuredAISummary` after one safe retry. Never raised for output we
    silently accepted; by the time this is raised, nothing malformed has
    been persisted."""

    status_code = status.HTTP_502_BAD_GATEWAY
    code = "ai_generation_failed"


def _error_response(status_code: int, code: str, message: str, details: object | None = None):
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        return _error_response(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException):
        return _error_response(
            exc.status_code,
            "http_error",
            exc.detail if isinstance(exc.detail, str) else "Request failed",
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        # `exc.errors()` can include a raw exception instance in `ctx` (for
        # any validator -- ours or Pydantic's own -- that raises a plain
        # ValueError), which plain `json.dumps` can't serialize.
        # `jsonable_encoder` converts it into a JSON-safe structure the same
        # way FastAPI's own default handler does.
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "validation_error",
            "One or more fields are invalid.",
            details=jsonable_encoder(exc.errors()),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        # Full detail goes to the server log only; the client gets a generic
        # message so we never leak internals or medical data in responses.
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_error",
            "An unexpected error occurred. Please try again later.",
        )
