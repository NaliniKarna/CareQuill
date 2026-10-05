from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.db import get_db
from app.models.user import User
from app.schemas.audit_log import AuditLogListResponse, AuditLogRead
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit-logs", tags=["audit"])

_MAX_LIMIT = 100


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    limit: int = Query(default=50, ge=1, le=_MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """The current patient's own security/audit trail (self-only). Never
    exposes another user's events."""
    service = AuditService(session)
    items, total = await service.list(user_id=current_user.id, limit=limit, offset=offset)
    return AuditLogListResponse(
        items=[AuditLogRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )
