import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.medical_document import MedicalDocument


class MedicalDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, patient_id: uuid.UUID, **fields) -> MedicalDocument:
        document = MedicalDocument(patient_id=patient_id, **fields)
        self.session.add(document)
        await self.session.flush()
        return document

    async def get_by_id_for_patient(
        self, document_id: uuid.UUID, patient_id: uuid.UUID
    ) -> MedicalDocument | None:
        result = await self.session.execute(
            select(MedicalDocument).where(
                MedicalDocument.id == document_id,
                MedicalDocument.patient_id == patient_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, document_id: uuid.UUID) -> MedicalDocument | None:
        """Unscoped lookup for internal (background task) use only -- never
        call this from a route/service acting on behalf of a request without
        a separate ownership check."""
        result = await self.session.execute(
            select(MedicalDocument).where(MedicalDocument.id == document_id)
        )
        return result.scalar_one_or_none()

    async def list_for_patient(
        self,
        patient_id: uuid.UUID,
        *,
        category: str | None = None,
        processing_status: str | None = None,
        q: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[MedicalDocument], int]:
        filters = [MedicalDocument.patient_id == patient_id]
        if category:
            filters.append(MedicalDocument.category == category)
        if processing_status:
            filters.append(MedicalDocument.processing_status == processing_status)
        if q:
            pattern = f"%{q}%"
            filters.append(
                or_(
                    MedicalDocument.title.ilike(pattern),
                    MedicalDocument.doctor_name.ilike(pattern),
                    MedicalDocument.hospital_name.ilike(pattern),
                )
            )

        count_result = await self.session.execute(
            select(func.count()).select_from(MedicalDocument).where(*filters)
        )
        total = count_result.scalar_one()

        result = await self.session.execute(
            select(MedicalDocument)
            .where(*filters)
            .order_by(MedicalDocument.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total

    async def list_all_for_patient(self, patient_id: uuid.UUID) -> list[MedicalDocument]:
        """Unpaginated listing for internal aggregation (the health
        timeline) -- never exposed directly over HTTP."""
        result = await self.session.execute(
            select(MedicalDocument).where(MedicalDocument.patient_id == patient_id)
        )
        return list(result.scalars().all())

    async def list_stuck(
        self, *, updated_before: datetime, limit: int = 50
    ) -> list[MedicalDocument]:
        """Documents left in `uploaded`/`processing` since before the cutoff -
        i.e. the server restarted (or crashed) while their background
        processing was running. Internal use only (startup recovery)."""
        result = await self.session.execute(
            select(MedicalDocument)
            .where(
                MedicalDocument.processing_status.in_(("uploaded", "processing")),
                MedicalDocument.updated_at < updated_before,
            )
            .order_by(MedicalDocument.updated_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        document: MedicalDocument,
        *,
        ocr_status: str | None = None,
        processing_status: str | None = None,
    ) -> MedicalDocument:
        if ocr_status is not None:
            document.ocr_status = ocr_status
        if processing_status is not None:
            document.processing_status = processing_status
        await self.session.flush()
        return document

    async def delete(self, document: MedicalDocument) -> None:
        await self.session.delete(document)
        await self.session.flush()
