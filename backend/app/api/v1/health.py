"""Infrastructure health checks -- not to be confused with patient health
data. Used by Docker healthchecks / uptime monitoring."""
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.db import get_db

router = APIRouter(tags=["system"])


@router.get("/health")
async def health_check():
    """Liveness check -- always returns ok if the process is up. Does not
    touch the database or any external integration."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness_check(response: Response, session: AsyncSession = Depends(get_db)):
    """Readiness check -- actually verifies the database is reachable.
    Deliberately does NOT check AI/OCR: those are optional integrations
    (AI_ENABLED/OCR_ENABLED can be false) and the app is still "ready"
    without them."""
    checks: dict[str, str] = {}
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "failed"

    if all(v == "ok" for v in checks.values()):
        return {"status": "ready", "checks": checks}

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "not_ready", "checks": checks}
