import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.medical_condition import MedicalCondition
from app.repositories.medical_condition_repository import MedicalConditionRepository
from app.schemas.medical_condition import MedicalConditionCreate, MedicalConditionUpdate
from app.services.health_snapshot_service import HealthSnapshotService


class MedicalConditionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = MedicalConditionRepository(session)
        self.snapshots = HealthSnapshotService(session)

    async def create(
        self, *, patient_id: uuid.UUID, data: MedicalConditionCreate
    ) -> MedicalCondition:
        condition = await self.repo.create(patient_id=patient_id, **data.model_dump())
        await self.snapshots.generate(patient_id=patient_id)
        return condition

    async def list(self, *, patient_id: uuid.UUID) -> list[MedicalCondition]:
        return await self.repo.list_for_patient(patient_id)

    async def get(self, *, patient_id: uuid.UUID, condition_id: uuid.UUID) -> MedicalCondition:
        condition = await self.repo.get_by_id_for_patient(condition_id, patient_id)
        if condition is None:
            raise NotFoundError("Medical condition not found.")
        return condition

    async def update(
        self, *, patient_id: uuid.UUID, condition_id: uuid.UUID, data: MedicalConditionUpdate
    ) -> MedicalCondition:
        condition = await self.get(patient_id=patient_id, condition_id=condition_id)
        updated = await self.repo.update(condition, **data.model_dump())
        await self.snapshots.generate(patient_id=patient_id)
        return updated

    async def delete(self, *, patient_id: uuid.UUID, condition_id: uuid.UUID) -> None:
        condition = await self.get(patient_id=patient_id, condition_id=condition_id)
        await self.repo.delete(condition)
        await self.snapshots.generate(patient_id=patient_id)
