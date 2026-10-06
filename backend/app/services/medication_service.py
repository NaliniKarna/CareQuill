import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.medication import Medication
from app.repositories.medication_repository import MedicationRepository
from app.schemas.medication import MedicationCreate, MedicationUpdate
from app.services.audit_service import AuditService
from app.services.health_snapshot_service import HealthSnapshotService
from app.services.provenance import resolve_provenance


class MedicationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = MedicationRepository(session)
        self.snapshots = HealthSnapshotService(session)
        self.audit = AuditService(session)

    async def create(self, *, patient_id: uuid.UUID, data: MedicationCreate) -> Medication:
        payload = data.model_dump(exclude={"source_document_id"})
        payload.update(
            await resolve_provenance(
                self.session, patient_id=patient_id, source_document_id=data.source_document_id
            )
        )
        medication = await self.repo.create(patient_id=patient_id, **payload)
        await self.snapshots.generate(patient_id=patient_id)
        await self.audit.record(
            user_id=patient_id,
            event_type="medication_create",
            resource_type="medication",
            resource_id=medication.id,
        )
        return medication

    async def list(
        self, *, patient_id: uuid.UUID, active: bool | None = None, q: str | None = None
    ) -> list[Medication]:
        return await self.repo.list_for_patient(patient_id, active=active, q=q)

    async def get(self, *, patient_id: uuid.UUID, medication_id: uuid.UUID) -> Medication:
        medication = await self.repo.get_by_id_for_patient(medication_id, patient_id)
        if medication is None:
            raise NotFoundError("Medication not found.")
        return medication

    async def update(
        self, *, patient_id: uuid.UUID, medication_id: uuid.UUID, data: MedicationUpdate
    ) -> Medication:
        medication = await self.get(patient_id=patient_id, medication_id=medication_id)
        updated = await self.repo.update(medication, **data.model_dump())
        await self.snapshots.generate(patient_id=patient_id)
        return updated

    async def delete(self, *, patient_id: uuid.UUID, medication_id: uuid.UUID) -> None:
        medication = await self.get(patient_id=patient_id, medication_id=medication_id)
        await self.repo.delete(medication)
        await self.snapshots.generate(patient_id=patient_id)

    async def set_active(
        self, *, patient_id: uuid.UUID, medication_id: uuid.UUID, is_active: bool
    ) -> Medication:
        medication = await self.get(patient_id=patient_id, medication_id=medication_id)
        updated = await self.repo.update(medication, is_active=is_active)
        await self.snapshots.generate(patient_id=patient_id)
        return updated
