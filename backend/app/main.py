import asyncio
import re
import time
from collections.abc import MutableMapping
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
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

_SLOW_REQUEST_MS = settings.slow_request_threshold_ms

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
        started = time.perf_counter()
        status_holder = {"status": 0}

        async def send_with_request_id(message: MutableMapping[str, Any]) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message.get("status", 0)
                elapsed_ms = (time.perf_counter() - started) * 1000
                response_headers = list(message.get("headers") or [])
                response_headers.append((_REQUEST_ID_HEADER, request_id.encode()))
                # Lets you see in the browser's Network tab how much of a
                # slow page load was the API (vs. the frontend).
                response_headers.append((b"x-process-time-ms", f"{elapsed_ms:.0f}".encode()))
                message["headers"] = response_headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            if elapsed_ms >= _SLOW_REQUEST_MS:
                logger.warning(
                    "Slow request: %s %s -> %s in %.0f ms",
                    scope.get("method"),
                    scope.get("path"),
                    status_holder["status"],
                    elapsed_ms,
                )
            reset_request_id(token)


class SecurityHeadersMiddleware:
    """Adds baseline hardening headers to every API response. API responses
    contain patient data, so they must never be stored by shared caches or
    the browser's disk cache; endpoints that stream files set their own
    Cache-Control."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._is_production = settings.environment == "production"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: MutableMapping[str, Any]) -> None:
            if message["type"] == "http.response.start":
                existing = {k.lower() for k, _ in (message.get("headers") or [])}
                extra: list[tuple[bytes, bytes]] = [
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
                ]
                if b"cache-control" not in existing:
                    extra.append((b"cache-control", b"no-store"))
                if self._is_production:
                    extra.append(
                        (b"strict-transport-security", b"max-age=63072000; includeSubDomains")
                    )
                message["headers"] = list(message.get("headers") or []) + [
                    h for h in extra if h[0] not in existing
                ]
            await send(message)

        await self.app(scope, receive, send_with_headers)


# Already-compressed or binary payloads (images, PDFs) gain nothing from gzip
# and would just burn CPU, so only JSON/text API responses are compressed.
_NO_GZIP_PATH = re.compile(r"/(download|preview|pdf)$")


class SelectiveGZipMiddleware:
    def __init__(self, app: ASGIApp, minimum_size: int = 1024) -> None:
        self.app = app
        self._gzip = GZipMiddleware(app, minimum_size=minimum_size)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and _NO_GZIP_PATH.search(scope.get("path", "")):
            await self.app(scope, receive, send)
            return
        await self._gzip(scope, receive, send)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "CareQuill backend starting | environment=%s ai_enabled=%s ocr_enabled=%s",
        settings.environment,
        settings.ai_enabled,
        settings.ocr_enabled,
    )
    recovery_task = None
    purge_task = None
    if not settings.is_test:
        # Re-queue documents whose background processing was interrupted by
        # a restart (kept as a task so a slow DB can't delay startup).
        from app.services.document_processing_service import recover_stuck_documents

        recovery_task = asyncio.create_task(recover_stuck_documents())
        from app.services.report_share_link_service import purge_expired_share_snapshots

        purge_task = asyncio.create_task(purge_expired_share_snapshots())
    yield
    if recovery_task is not None and not recovery_task.done():
        recovery_task.cancel()
    if purge_task is not None and not purge_task.done():
        purge_task.cancel()
    logger.info("CareQuill backend shutting down")


app = FastAPI(
    title=settings.project_name,
    description=(
        "CareQuill backend API. Designed with privacy and security "
        "principles appropriate for handling sensitive health information. "
        "This application does not diagnose conditions, prescribe treatment, "
        "or act as an autonomous medical decision-maker."
    ),
    version="0.1.0",
    # Interactive API docs list every endpoint; keep them for development
    # only.
    openapi_url=(
        None if settings.environment == "production" else f"{settings.api_v1_prefix}/openapi.json"
    ),
    docs_url=None if settings.environment == "production" else f"{settings.api_v1_prefix}/docs",
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SelectiveGZipMiddleware)
app.add_middleware(RequestIDMiddleware)

register_exception_handlers(app)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
async def root():
    return {
        "name": settings.project_name,
        "status": "ok",
    }
