import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.allergy import Allergy
from app.repositories.allergy_repository import AllergyRepository
from app.schemas.allergy import AllergyCreate, AllergyUpdate
from app.services.health_snapshot_service import HealthSnapshotService
from app.services.provenance import resolve_provenance


class AllergyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AllergyRepository(session)
        self.snapshots = HealthSnapshotService(session)

    async def create(self, *, patient_id: uuid.UUID, data: AllergyCreate) -> Allergy:
        payload = data.model_dump(exclude={"source_document_id"})
        payload.update(
            await resolve_provenance(
                self.session, patient_id=patient_id, source_document_id=data.source_document_id
            )
        )
        allergy = await self.repo.create(patient_id=patient_id, **payload)
        await self.snapshots.generate(patient_id=patient_id)
        return allergy

    async def list(self, *, patient_id: uuid.UUID) -> list[Allergy]:
        return await self.repo.list_for_patient(patient_id)

    async def get(self, *, patient_id: uuid.UUID, allergy_id: uuid.UUID) -> Allergy:
        allergy = await self.repo.get_by_id_for_patient(allergy_id, patient_id)
        if allergy is None:
            raise NotFoundError("Allergy not found.")
        return allergy

    async def update(
        self, *, patient_id: uuid.UUID, allergy_id: uuid.UUID, data: AllergyUpdate
    ) -> Allergy:
        allergy = await self.get(patient_id=patient_id, allergy_id=allergy_id)
        updated = await self.repo.update(allergy, **data.model_dump())
        await self.snapshots.generate(patient_id=patient_id)
        return updated

    async def delete(self, *, patient_id: uuid.UUID, allergy_id: uuid.UUID) -> None:
        allergy = await self.get(patient_id=patient_id, allergy_id=allergy_id)
        await self.repo.delete(allergy)
        await self.snapshots.generate(patient_id=patient_id)
