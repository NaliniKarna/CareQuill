import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_log import EmailLog
from app.repositories.email_log_repository import EmailLogRepository


class EmailLogService:
    """Read-only access to a patient's own sharing history (both AI-summary
    shares and full health-report shares land in the same `email_logs`
    table)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = EmailLogRepository(session)

    async def list(self, *, patient_id: uuid.UUID) -> list[EmailLog]:
        return await self.repo.list_for_patient(patient_id)
