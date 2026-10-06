import uuid
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.journal_entry import JournalEntry


class JournalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, patient_id: uuid.UUID, **fields) -> JournalEntry:
        entry = JournalEntry(patient_id=patient_id, **fields)
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def get_by_id_for_patient(
        self, entry_id: uuid.UUID, patient_id: uuid.UUID
    ) -> JournalEntry | None:
        result = await self.session.execute(
            select(JournalEntry).where(
                JournalEntry.id == entry_id, JournalEntry.patient_id == patient_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_patient(
        self,
        patient_id: uuid.UUID,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        q: str | None = None,
        limit: int = 30,
        offset: int = 0,
    ) -> tuple[list[JournalEntry], int]:
        conditions = [JournalEntry.patient_id == patient_id]
        if date_from:
            conditions.append(JournalEntry.entry_date >= date_from)
        if date_to:
            conditions.append(JournalEntry.entry_date <= date_to)
        if q:
            like = f"%{q.strip().replace('%', '').replace('_', '')}%"
            conditions.append(
                or_(JournalEntry.body.ilike(like), JournalEntry.title.ilike(like))
            )
        count_stmt = select(func.count()).select_from(JournalEntry).where(*conditions)
        total = (await self.session.execute(count_stmt)).scalar_one()
        rows = await self.session.execute(
            select(JournalEntry)
            .where(*conditions)
            .order_by(JournalEntry.entry_date.desc(), JournalEntry.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(rows.scalars().all()), total

    async def update(self, entry: JournalEntry, **fields) -> JournalEntry:
        for key, value in fields.items():
            setattr(entry, key, value)
        await self.session.flush()
        return entry

    async def delete(self, entry: JournalEntry) -> None:
        await self.session.delete(entry)
        await self.session.flush()
