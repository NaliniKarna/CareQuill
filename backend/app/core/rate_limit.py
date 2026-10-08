"""
Small in-process sliding-window rate limiter for abuse-prone endpoints
(login, registration, password reset, AI generation, uploads).

Scope and honesty: the counters live in this process's memory. That is
correct for a single worker and still a useful brake with several workers
(each enforces its own window, so the effective limit is N x configured),
but it is NOT a distributed limiter. For a multi-host deployment put a
reverse proxy / API gateway limit in front (see docs/deployment.md) or swap
`_hits` for Redis behind this same dependency.

The client key is the connection's IP. Behind a reverse proxy, run uvicorn/
gunicorn with `--forwarded-allow-ips` set to the proxy so `request.client`
is the real client rather than the proxy itself.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import Request

from app.core.config import settings
from app.core.exceptions import AppError

_MAX_TRACKED_KEYS = 50_000


class RateLimitedError(AppError):
    status_code = 429
    code = "rate_limited"


_hits: dict[str, deque[float]] = defaultdict(deque)


def _prune(now: float) -> None:
    """Bound memory: drop idle keys when the table grows large."""
    if len(_hits) < _MAX_TRACKED_KEYS:
        return
    for key in [k for k, q in _hits.items() if not q or now - q[-1] > 3600]:
        _hits.pop(key, None)


def reset_rate_limits() -> None:
    """For tests."""
    _hits.clear()


def rate_limit(group: str, *, attempts_attr: str, window_attr: str) -> Callable:
    """FastAPI dependency factory. Limits are read from settings at request
    time (so they can be tuned/tested without rebuilding the app)."""

    async def dependency(request: Request) -> None:
        if not settings.rate_limit_enabled:
            return
        attempts = getattr(settings, attempts_attr)
        window = getattr(settings, window_attr)
        client = request.client.host if request.client else "unknown"
        key = f"{group}:{client}"

        now = time.monotonic()
        queue = _hits[key]
        while queue and now - queue[0] > window:
            queue.popleft()
        if len(queue) >= attempts:
            retry_after = max(1, int(window - (now - queue[0])))
            raise RateLimitedError(
                f"Too many requests. Please wait {retry_after} seconds and try again.",
                details={"retry_after_seconds": retry_after},
            )
        queue.append(now)
        _prune(now)

    return dependency


auth_rate_limit = rate_limit(
    "auth",
    attempts_attr="auth_rate_limit_attempts",
    window_attr="auth_rate_limit_window_seconds",
)
ai_rate_limit = rate_limit(
    "ai", attempts_attr="ai_rate_limit_attempts", window_attr="ai_rate_limit_window_seconds"
)
shared_link_rate_limit = rate_limit(
    "shared_link",
    attempts_attr="shared_link_rate_limit_attempts",
    window_attr="shared_link_rate_limit_window_seconds",
)
upload_rate_limit = rate_limit(
    "upload",
    attempts_attr="upload_rate_limit_attempts",
    window_attr="upload_rate_limit_window_seconds",
)
family_claim_rate_limit = rate_limit(
    "family_claim",
    attempts_attr="auth_rate_limit_attempts",
    window_attr="auth_rate_limit_window_seconds",
)
contact_rate_limit = rate_limit(
    "contact",
    attempts_attr="contact_rate_limit_attempts",
    window_attr="contact_rate_limit_window_seconds",
)
