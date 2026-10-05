import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.allergy import Allergy


class AllergyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, patient_id: uuid.UUID, **fields) -> Allergy:
        allergy = Allergy(patient_id=patient_id, **fields)
        self.session.add(allergy)
        await self.session.flush()
        return allergy

    async def get_by_id_for_patient(
        self, allergy_id: uuid.UUID, patient_id: uuid.UUID
    ) -> Allergy | None:
        result = await self.session.execute(
            select(Allergy).where(Allergy.id == allergy_id, Allergy.patient_id == patient_id)
        )
        return result.scalar_one_or_none()

    async def list_for_patient(self, patient_id: uuid.UUID) -> list[Allergy]:
        result = await self.session.execute(
            select(Allergy)
            .where(Allergy.patient_id == patient_id)
            .order_by(Allergy.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, allergy: Allergy, **fields) -> Allergy:
        for key, value in fields.items():
            setattr(allergy, key, value)
        await self.session.flush()
        return allergy

    async def delete(self, allergy: Allergy) -> None:
        await self.session.delete(allergy)
        await self.session.flush()
