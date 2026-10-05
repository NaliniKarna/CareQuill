import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_log import EmailLog


class EmailLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, patient_id: uuid.UUID, **fields) -> EmailLog:
        log = EmailLog(patient_id=patient_id, **fields)
        self.session.add(log)
        await self.session.flush()
        return log

    async def list_for_patient(self, patient_id: uuid.UUID) -> list[EmailLog]:
        result = await self.session.execute(
            select(EmailLog)
            .where(EmailLog.patient_id == patient_id)
            .order_by(EmailLog.created_at.desc())
        )
        return list(result.scalars().all())
