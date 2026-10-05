import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_extraction import DocumentExtraction
from app.models.medical_document import MedicalDocument


class DocumentExtractionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, document_id: uuid.UUID, **fields) -> DocumentExtraction:
        extraction = DocumentExtraction(document_id=document_id, **fields)
        self.session.add(extraction)
        await self.session.flush()
        return extraction

    async def get_by_document_id(self, document_id: uuid.UUID) -> DocumentExtraction | None:
        result = await self.session.execute(
            select(DocumentExtraction).where(DocumentExtraction.document_id == document_id)
        )
        return result.scalar_one_or_none()

    async def update(self, extraction: DocumentExtraction, **fields) -> DocumentExtraction:
        for key, value in fields.items():
            setattr(extraction, key, value)
        await self.session.flush()
        return extraction

    async def list_reviewed_for_patient(self, patient_id: uuid.UUID) -> list[DocumentExtraction]:
        """Reviewed extractions belonging to documents owned by this
        patient -- used by the timeline (tagged AI_EXTRACTED, never
        upgraded to VERIFIED)."""
        result = await self.session.execute(
            select(DocumentExtraction)
            .join(MedicalDocument, DocumentExtraction.document_id == MedicalDocument.id)
            .where(
                MedicalDocument.patient_id == patient_id,
                DocumentExtraction.status == "reviewed",
            )
        )
        return list(result.scalars().all())
