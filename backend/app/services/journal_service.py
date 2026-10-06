import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.journal_entry import JournalEntry
from app.repositories.journal_repository import JournalRepository
from app.schemas.journal import JournalEntryCreate, JournalEntryUpdate


class JournalService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = JournalRepository(session)

    async def create(self, *, patient_id: uuid.UUID, data: JournalEntryCreate) -> JournalEntry:
        return await self.repo.create(patient_id=patient_id, **data.model_dump())

    async def list(
        self,
        *,
        patient_id: uuid.UUID,
        date_from: date | None,
        date_to: date | None,
        q: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[JournalEntry], int]:
        return await self.repo.list_for_patient(
            patient_id, date_from=date_from, date_to=date_to, q=q, limit=limit, offset=offset
        )

    async def get(self, *, patient_id: uuid.UUID, entry_id: uuid.UUID) -> JournalEntry:
        entry = await self.repo.get_by_id_for_patient(entry_id, patient_id)
        if entry is None:
            raise NotFoundError("Journal entry not found.")
        return entry

    async def update(
        self, *, patient_id: uuid.UUID, entry_id: uuid.UUID, data: JournalEntryUpdate
    ) -> JournalEntry:
        entry = await self.get(patient_id=patient_id, entry_id=entry_id)
        return await self.repo.update(entry, **data.model_dump())

    async def delete(self, *, patient_id: uuid.UUID, entry_id: uuid.UUID) -> None:
        entry = await self.get(patient_id=patient_id, entry_id=entry_id)
        await self.repo.delete(entry)
