from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.db import get_db
from app.models.user import User
from app.schemas.email_log import EmailLogListItem
from app.services.email_log_service import EmailLogService

router = APIRouter(prefix="/email-logs", tags=["email-logs"])


@router.get("", response_model=list[EmailLogListItem])
async def list_email_logs(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """The current patient's sharing history (doctor, appointment, sent
    date, status, report name) -- never the attached document/summary
    content or the full `included_sections` breakdown."""
    service = EmailLogService(session)
    logs = await service.list(patient_id=current_user.id)
    return [EmailLogListItem.model_validate(log) for log in logs]
