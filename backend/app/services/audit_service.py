"""
Tiny, one-liner-per-call-site audit trail. Intentionally does nothing else:
no business logic, no branching on event type. Called from other services
at the point an auditable action happens (see each event type's call site)
-- never logs passwords, tokens, or medical content, only event type +
resource identifiers.
"""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.audit_log_repository import AuditLogRepository


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AuditLogRepository(session)

    async def record(
        self,
        *,
        user_id: uuid.UUID | None,
        event_type: str,
        resource_type: str | None = None,
        resource_id: uuid.UUID | str | None = None,
    ) -> None:
        await self.repo.create(
            user_id=user_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
        )

    async def list(
        self, *, user_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> tuple[list, int]:
        return await self.repo.list_for_user(user_id, limit=limit, offset=offset)
