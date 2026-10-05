import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_summary import AISummary


class AISummaryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, patient_id: uuid.UUID, **fields) -> AISummary:
        summary = AISummary(patient_id=patient_id, **fields)
        self.session.add(summary)
        await self.session.flush()
        return summary

    async def get_by_id_for_patient(
        self, summary_id: uuid.UUID, patient_id: uuid.UUID
    ) -> AISummary | None:
        result = await self.session.execute(
            select(AISummary).where(
                AISummary.id == summary_id, AISummary.patient_id == patient_id
            )
        )
        return result.scalar_one_or_none()

    async def update(self, summary: AISummary, **fields) -> AISummary:
        for key, value in fields.items():
            setattr(summary, key, value)
        await self.session.flush()
        return summary

    async def mark_stale_summaries_outdated(self, patient_id: uuid.UUID) -> None:
        """Marks every `pending_review`/`reviewed` summary for this patient
        as `outdated`. Never touches `shared` summaries (already-shared
        history is immutable) and never deletes anything."""
        await self.session.execute(
            update(AISummary)
            .where(
                AISummary.patient_id == patient_id,
                AISummary.status.in_(("pending_review", "reviewed")),
            )
            .values(status="outdated")
        )
        await self.session.flush()

    async def list_for_patient(self, patient_id: uuid.UUID) -> list[AISummary]:
        result = await self.session.execute(
            select(AISummary)
            .where(AISummary.patient_id == patient_id)
            .order_by(AISummary.created_at.desc())
        )
        return list(result.scalars().all())
