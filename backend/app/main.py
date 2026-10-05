from collections.abc import MutableMapping
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import (
    configure_logging,
    logger,
    new_request_id,
    reset_request_id,
    set_request_id,
)

configure_logging()

_REQUEST_ID_HEADER = b"x-request-id"


class RequestIDMiddleware:
    """Assigns each request a correlation id -- the client's own
    `X-Request-ID` if it sent one, otherwise a freshly generated one -- and
    both threads it into every log record for this request (via a
    contextvar, see app.core.logging) and echoes it back in the response
    header, so a client/log aggregator can trace one request end-to-end.

    Implemented as a plain ASGI middleware (not `@app.middleware("http")`,
    which wraps `BaseHTTPMiddleware`) deliberately: `BaseHTTPMiddleware` is
    known to interfere with how an unhandled exception reaches Starlette's
    `ServerErrorMiddleware` (it can mark the response as already "started"
    before the exception propagates, so the generic-error JSON response
    from `app.core.exceptions` never gets sent). A raw ASGI middleware has
    no such interaction -- it never touches the response's body/streaming."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        request_id = headers.get(_REQUEST_ID_HEADER, b"").decode() or new_request_id()
        token = set_request_id(request_id)

        async def send_with_request_id(message: MutableMapping[str, Any]) -> None:
            if message["type"] == "http.response.start":
                response_headers = list(message.get("headers") or [])
                response_headers.append((_REQUEST_ID_HEADER, request_id.encode()))
                message["headers"] = response_headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            reset_request_id(token)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "MedQueue AI backend starting | environment=%s ai_enabled=%s ocr_enabled=%s",
        settings.environment,
        settings.ai_enabled,
        settings.ocr_enabled,
    )
    yield
    logger.info("MedQueue AI backend shutting down")


app = FastAPI(
    title=settings.project_name,
    description=(
        "Med AI / MedQueue AI backend API. Designed with privacy and security "
        "principles appropriate for handling sensitive health information. "
        "This application does not diagnose conditions, prescribe treatment, "
        "or act as an autonomous medical decision-maker."
    ),
    version="0.1.0",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url=f"{settings.api_v1_prefix}/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)

register_exception_handlers(app)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
async def root():
    return {
        "name": settings.project_name,
        "status": "ok",
        "docs": f"{settings.api_v1_prefix}/docs",
    }
