import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.timeline_note import TimelineNote


class TimelineNoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, patient_id: uuid.UUID, **fields) -> TimelineNote:
        note = TimelineNote(patient_id=patient_id, **fields)
        self.session.add(note)
        await self.session.flush()
        return note

    async def get_by_id_for_patient(
        self, note_id: uuid.UUID, patient_id: uuid.UUID
    ) -> TimelineNote | None:
        result = await self.session.execute(
            select(TimelineNote).where(
                TimelineNote.id == note_id, TimelineNote.patient_id == patient_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_patient(self, patient_id: uuid.UUID) -> list[TimelineNote]:
        result = await self.session.execute(
            select(TimelineNote)
            .where(TimelineNote.patient_id == patient_id)
            .order_by(TimelineNote.event_date.desc())
        )
        return list(result.scalars().all())

    async def delete(self, note: TimelineNote) -> None:
        await self.session.delete(note)
        await self.session.flush()
