import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, patient_id: uuid.UUID, **fields) -> Notification:
        notification = Notification(patient_id=patient_id, **fields)
        self.session.add(notification)
        await self.session.flush()
        return notification

    async def get_by_id_for_patient(
        self, notification_id: uuid.UUID, patient_id: uuid.UUID
    ) -> Notification | None:
        result = await self.session.execute(
            select(Notification).where(
                Notification.id == notification_id, Notification.patient_id == patient_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_patient(
        self, patient_id: uuid.UUID, *, unread_only: bool = False
    ) -> list[Notification]:
        filters = [Notification.patient_id == patient_id]
        if unread_only:
            filters.append(Notification.is_read.is_(False))
        result = await self.session.execute(
            select(Notification).where(*filters).order_by(Notification.created_at.desc())
        )
        return list(result.scalars().all())

    async def mark_read(self, notification: Notification) -> Notification:
        notification.is_read = True
        await self.session.flush()
        return notification
