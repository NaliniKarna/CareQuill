"""
Provenance for patient-entered records.

When the patient reviews an AI/OCR suggestion on one of their documents and
chooses to add it to their Medications / Allergies / Conditions, the new
record remembers which document it was confirmed from. This is how
"AI-extracted information becomes verified only after patient review" is
represented in the data: the patient is the one who creates the record
(through the normal create endpoint, with the same validation), and the link
back to the source document is verified here - the document must belong to
the same patient (IDOR guard).
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.repositories.medical_document_repository import MedicalDocumentRepository

SOURCE_MANUAL = "manual"
SOURCE_DOCUMENT_EXTRACTION = "document_extraction"


async def resolve_provenance(
    session: AsyncSession, *, patient_id: uuid.UUID, source_document_id: uuid.UUID | None
) -> dict:
    if source_document_id is None:
        return {"source": SOURCE_MANUAL, "source_document_id": None}
    document = await MedicalDocumentRepository(session).get_by_id_for_patient(
        source_document_id, patient_id
    )
    if document is None:
        # Same response as any other missing resource: never reveal that a
        # document id exists but belongs to someone else.
        raise NotFoundError("Source document not found.")
    return {"source": SOURCE_DOCUMENT_EXTRACTION, "source_document_id": document.id}
