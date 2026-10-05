import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.medical_condition import MedicalCondition


class MedicalConditionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, patient_id: uuid.UUID, **fields) -> MedicalCondition:
        condition = MedicalCondition(patient_id=patient_id, **fields)
        self.session.add(condition)
        await self.session.flush()
        return condition

    async def get_by_id_for_patient(
        self, condition_id: uuid.UUID, patient_id: uuid.UUID
    ) -> MedicalCondition | None:
        result = await self.session.execute(
            select(MedicalCondition).where(
                MedicalCondition.id == condition_id, MedicalCondition.patient_id == patient_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_patient(self, patient_id: uuid.UUID) -> list[MedicalCondition]:
        result = await self.session.execute(
            select(MedicalCondition)
            .where(MedicalCondition.patient_id == patient_id)
            .order_by(MedicalCondition.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, condition: MedicalCondition, **fields) -> MedicalCondition:
        for key, value in fields.items():
            setattr(condition, key, value)
        await self.session.flush()
        return condition

    async def delete(self, condition: MedicalCondition) -> None:
        await self.session.delete(condition)
        await self.session.flush()
