import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditLogRepository:
    """Append-only -- deliberately no update()/delete() methods, matching
    the immutability rule for audit history."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        user_id: uuid.UUID | None,
        event_type: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            user_id=user_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def list_for_user(
        self, user_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> tuple[list[AuditLog], int]:
        count_result = await self.session.execute(
            select(func.count()).select_from(AuditLog).where(AuditLog.user_id == user_id)
        )
        total = count_result.scalar_one()

        result = await self.session.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total
