import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.db import get_db
from app.models.user import User
from app.schemas.notification import NotificationRead
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead])
async def list_notifications(
    unread_only: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Merges persisted notifications (AI summary ready, document
    processed, report shared, email failure) with computed-on-read ones
    (appointment approaching within 48 hours, medication reminder due
    today), newest first. `unread_only` only filters persisted rows --
    computed notifications are always considered unread/informational and
    are always included."""
    service = NotificationService(session)
    return await service.list(patient_id=current_user.id, unread_only=unread_only)


@router.patch("/{notification_id}/read", response_model=NotificationRead)
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Marks a persisted notification read. 404s for a computed
    notification's id (it never matches a stored row) or one belonging to
    another patient."""
    service = NotificationService(session)
    return await service.mark_read(patient_id=current_user.id, notification_id=notification_id)
