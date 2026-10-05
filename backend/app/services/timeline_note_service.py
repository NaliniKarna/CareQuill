import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.timeline_note import TimelineNote
from app.repositories.timeline_note_repository import TimelineNoteRepository
from app.schemas.timeline import TimelineNoteCreate


class TimelineNoteService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = TimelineNoteRepository(session)

    async def create(self, *, patient_id: uuid.UUID, data: TimelineNoteCreate) -> TimelineNote:
        return await self.repo.create(patient_id=patient_id, **data.model_dump())

    async def list(self, *, patient_id: uuid.UUID) -> list[TimelineNote]:
        return await self.repo.list_for_patient(patient_id)

    async def delete(self, *, patient_id: uuid.UUID, note_id: uuid.UUID) -> None:
        note = await self.repo.get_by_id_for_patient(note_id, patient_id)
        if note is None:
            raise NotFoundError("Timeline note not found.")
        await self.repo.delete(note)
