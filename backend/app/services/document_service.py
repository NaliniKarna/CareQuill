import os
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_ai_provider
from app.core.config import settings
from app.core.exceptions import AIGenerationError, NotFoundError, ValidationAppError
from app.models.document_extraction import DocumentExtraction
from app.models.medical_document import MedicalDocument
from app.repositories.document_extraction_repository import DocumentExtractionRepository
from app.repositories.medical_document_repository import MedicalDocumentRepository
from app.repositories.user_preference_repository import UserPreferenceRepository
from app.schemas.document_extraction import DocumentExtractionStatusUpdate
from app.schemas.medical_document import MedicalDocumentUploadForm
from app.services.audit_service import AuditService
from app.services.document_ai_service import explain_with_ai
from app.storage.factory import get_storage_backend
from app.utils.files import (
    bytes_match_claimed_extension,
    generate_stored_filename,
    is_extension_allowed,
    sanitize_filename,
)


class DocumentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = MedicalDocumentRepository(session)
        self.extraction_repo = DocumentExtractionRepository(session)
        self.storage = get_storage_backend()
        self.audit = AuditService(session)

    async def upload(
        self,
        *,
        patient_id: uuid.UUID,
        file_bytes: bytes,
        original_filename: str,
        form: MedicalDocumentUploadForm,
    ) -> MedicalDocument:
        self._validate_file(file_bytes=file_bytes, original_filename=original_filename)

        safe_original_name = sanitize_filename(original_filename)
        stored_filename = generate_stored_filename(original_filename)
        storage_path = await self.storage.save(relative_path=stored_filename, content=file_bytes)

        mime_type = _mime_type_for_extension(original_filename)

        document = await self.repo.create(
            patient_id=patient_id,
            title=form.title,
            category=form.category,
            original_filename=safe_original_name,
            stored_filename=stored_filename,
            storage_path=storage_path,
            mime_type=mime_type,
            file_size=len(file_bytes),
            visit_date=form.visit_date,
            doctor_name=form.doctor_name,
            hospital_name=form.hospital_name,
            ocr_status="pending",
            processing_status="uploaded",
        )
        await self.audit.record(
            user_id=patient_id,
            event_type="document_upload",
            resource_type="medical_document",
            resource_id=document.id,
        )
        return document

    def _validate_file(self, *, file_bytes: bytes, original_filename: str) -> None:
        if not file_bytes:
            raise ValidationAppError("Uploaded file is empty.")

        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        if len(file_bytes) > max_bytes:
            raise ValidationAppError(
                f"File exceeds the maximum allowed size of {settings.max_upload_size_mb} MB."
            )

        if not is_extension_allowed(original_filename, settings.allowed_upload_extensions_list):
            raise ValidationAppError(
                "Unsupported file type. Allowed types: "
                + ", ".join(settings.allowed_upload_extensions_list)
            )

        if not bytes_match_claimed_extension(file_bytes, original_filename):
            raise ValidationAppError(
                "The file's contents do not match its file extension."
            )

    async def list(
        self,
        *,
        patient_id: uuid.UUID,
        category: str | None,
        processing_status: str | None,
        q: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[MedicalDocument], int]:
        return await self.repo.list_for_patient(
            patient_id,
            category=category,
            processing_status=processing_status,
            q=q,
            limit=limit,
            offset=offset,
        )

    async def get(self, *, patient_id: uuid.UUID, document_id: uuid.UUID) -> MedicalDocument:
        document = await self.repo.get_by_id_for_patient(document_id, patient_id)
        if document is None:
            raise NotFoundError("Document not found.")
        return document

    async def get_file_bytes(
        self, *, patient_id: uuid.UUID, document_id: uuid.UUID
    ) -> tuple[MedicalDocument, bytes]:
        document = await self.get(patient_id=patient_id, document_id=document_id)
        try:
            content = await self.storage.read(storage_path=document.storage_path)
        except FileNotFoundError as exc:
            raise NotFoundError("The document's file could not be found.") from exc
        return document, content

    async def delete(self, *, patient_id: uuid.UUID, document_id: uuid.UUID) -> None:
        document = await self.get(patient_id=patient_id, document_id=document_id)
        await self.storage.delete(storage_path=document.storage_path)
        await self.repo.delete(document)
        await self.audit.record(
            user_id=patient_id,
            event_type="document_delete",
            resource_type="medical_document",
            resource_id=document_id,
        )

    async def get_extraction(
        self, *, patient_id: uuid.UUID, document_id: uuid.UUID
    ) -> DocumentExtraction:
        # Ownership check on the parent document first.
        document = await self.get(patient_id=patient_id, document_id=document_id)
        extraction = await self.extraction_repo.get_by_document_id(document.id)
        if extraction is None:
            raise NotFoundError(
                "No extraction is available for this document yet "
                "(it may still be processing, or processing may have been skipped)."
            )
        return extraction

    async def reprocess(self, *, patient_id: uuid.UUID, document_id: uuid.UUID) -> MedicalDocument:
        """Re-queues OCR/extraction for an existing upload (e.g. after the
        server's OCR was switched on, or after a failure). The original file
        is untouched; the previous extraction is replaced and returns to
        "pending review"."""
        document = await self.get(patient_id=patient_id, document_id=document_id)
        if document.processing_status == "processing":
            raise ValidationAppError("This document is already being processed.")
        document = await self.repo.update_status(
            document, ocr_status="pending", processing_status="uploaded"
        )
        await self.audit.record(
            user_id=patient_id,
            event_type="document_reprocess",
            resource_type="medical_document",
            resource_id=document_id,
        )
        return document

    async def explain(self, *, patient_id: uuid.UUID, document_id: uuid.UUID) -> dict:
        """Generates (and stores on the extraction) a plain-language
        explanation of the document's text. Explicit patient action; never
        run automatically."""
        if not settings.ai_enabled or not settings.ai_document_explain_enabled:
            raise ValidationAppError(
                "AI explanations aren't enabled for this deployment."
            )
        preference = await UserPreferenceRepository(self.session).get_by_user_id(patient_id)
        if preference is not None and not preference.data_sharing_consent:
            raise ValidationAppError(
                "AI processing of your documents is turned off in your privacy settings."
            )

        extraction = await self.get_extraction(patient_id=patient_id, document_id=document_id)
        if (extraction.extracted_data or {}).get("document_kind") == "medical_image":
            raise ValidationAppError(
                "Medical images aren't interpreted. Upload the written report to get "
                "an explanation of its wording."
            )

        provider = get_ai_provider()
        if not await provider.is_available():
            raise AIGenerationError(
                "The AI service isn't available right now. Please try again later."
            )

        explanation = await explain_with_ai(
            provider=provider,
            document_text=extraction.raw_text or "",
            model_name=getattr(provider, "model", "ai"),
        )
        await self.extraction_repo.update(
            extraction,
            extracted_data={**(extraction.extracted_data or {}), "explanation": explanation},
        )
        await self.audit.record(
            user_id=patient_id,
            event_type="document_explain",
            resource_type="medical_document",
            resource_id=document_id,
        )
        return explanation

    async def update_extraction_status(
        self,
        *,
        patient_id: uuid.UUID,
        document_id: uuid.UUID,
        data: DocumentExtractionStatusUpdate,
    ) -> DocumentExtraction:
        """Marks the extraction reviewed/dismissed only. See the docstring
        on `DocumentExtractionStatusUpdate` -- this never writes into
        allergies/medications/conditions."""
        extraction = await self.get_extraction(patient_id=patient_id, document_id=document_id)
        return await self.extraction_repo.update(extraction, status=data.status)


_EXTENSION_MIME_MAP = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def _mime_type_for_extension(filename: str) -> str:
    suffix = os.path.splitext(filename)[1].lower()
    return _EXTENSION_MIME_MAP.get(suffix, "application/octet-stream")
