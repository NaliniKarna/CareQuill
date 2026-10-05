"""
Background OCR + structured-entity-extraction pipeline, kicked off (via
FastAPI `BackgroundTasks`) right after a document upload so the upload
response never blocks on OCR.

Runs in its OWN database session (`app.db.session.session_scope`) rather
than the request's session, because a background task executes *after* the
response has been sent -- by then the request-scoped session from
`Depends(get_db)` has already been closed.

The whole pipeline is wrapped in try/except: a processing failure is logged
server-side only (never leaked into a document's fields) and always results
in `ocr_status="failed"` / `processing_status="failed"` rather than leaving
a document stuck at "processing" forever.
"""
from __future__ import annotations

import uuid

from app.core.logging import logger
from app.db.session import session_scope
from app.ocr.factory import get_ocr_engine
from app.ocr.interface import OCREngine
from app.repositories.document_extraction_repository import DocumentExtractionRepository
from app.repositories.medical_document_repository import MedicalDocumentRepository
from app.repositories.user_preference_repository import UserPreferenceRepository
from app.services.entity_extraction_service import clean_text, extract_entities
from app.services.notification_service import NotificationService
from app.storage.factory import get_storage_backend

_MIN_TEXT_LAYER_LENGTH = 20  # below this, treat a PDF as having no usable text layer
_PDF_RENDER_DPI = 200

_SUPPORTED_IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/jpg"}


async def process_document(document_id: uuid.UUID) -> None:
    """Entry point called from the upload route's BackgroundTasks."""
    try:
        await _run_pipeline(document_id)
    except Exception:
        # Full detail server-side only; never surfaced to the patient.
        logger.exception("Document processing failed for document_id=%s", document_id)
        await _mark_failed(document_id)


async def _run_pipeline(document_id: uuid.UUID) -> None:
    async with session_scope() as session:
        document_repo = MedicalDocumentRepository(session)
        extraction_repo = DocumentExtractionRepository(session)

        document = await document_repo.get_by_id(document_id)
        if document is None:
            return

        preferences = UserPreferenceRepository(session)
        preference = await preferences.get_by_user_id(document.patient_id)
        if preference is not None and not preference.data_sharing_consent:
            # The patient has opted out of automatic OCR/AI processing --
            # never process this (or any future) upload of theirs until
            # they turn it back on. The file itself is still kept.
            await document_repo.update_status(
                document, ocr_status="skipped", processing_status="processed"
            )
            return

        await document_repo.update_status(document, processing_status="processing")

        storage = get_storage_backend()
        try:
            file_bytes = await storage.read(storage_path=document.storage_path)
        except FileNotFoundError:
            logger.error("Document %s: file missing from storage during OCR.", document_id)
            await document_repo.update_status(
                document, ocr_status="failed", processing_status="failed"
            )
            return

        ocr_engine = get_ocr_engine()
        raw_text, confidence = await _extract_text(
            file_bytes=file_bytes, mime_type=document.mime_type, ocr_engine=ocr_engine
        )

        if raw_text is None:
            # Unsupported mime type for extraction (shouldn't normally
            # happen given upload-time validation, but fail safe).
            await document_repo.update_status(
                document, ocr_status="skipped", processing_status="processed"
            )
            return

        cleaned = clean_text(raw_text)
        extracted_data = extract_entities(cleaned)

        existing = await extraction_repo.get_by_document_id(document.id)
        if existing is None:
            await extraction_repo.create(
                document_id=document.id,
                raw_text=cleaned,
                confidence=confidence,
                extracted_data=extracted_data,
                status="pending_review",
            )
        else:
            await extraction_repo.update(
                existing,
                raw_text=cleaned,
                confidence=confidence,
                extracted_data=extracted_data,
            )

        await document_repo.update_status(
            document, ocr_status="completed", processing_status="processed"
        )

        notifications = NotificationService(session)
        await notifications.notify(
            patient_id=document.patient_id,
            type="document_processed",
            title="Document processed",
            body=f"'{document.title}' has finished processing and is ready to review.",
            related_resource_id=document.id,
        )


async def _mark_failed(document_id: uuid.UUID) -> None:
    try:
        async with session_scope() as session:
            document_repo = MedicalDocumentRepository(session)
            document = await document_repo.get_by_id(document_id)
            if document is not None:
                await document_repo.update_status(
                    document, ocr_status="failed", processing_status="failed"
                )
    except Exception:
        logger.exception(
            "Failed to mark document %s as failed after a processing error.", document_id
        )


async def _extract_text(
    *, file_bytes: bytes, mime_type: str, ocr_engine: OCREngine
) -> tuple[str | None, float | None]:
    if mime_type == "application/pdf":
        return await _extract_pdf_text(file_bytes, ocr_engine)
    if mime_type in _SUPPORTED_IMAGE_MIME_TYPES:
        result = await ocr_engine.extract(file_bytes=file_bytes, mime_type=mime_type)
        return result.raw_text, result.confidence
    return None, None


async def _extract_pdf_text(
    file_bytes: bytes, ocr_engine: OCREngine
) -> tuple[str, float | None]:
    import fitz  # PyMuPDF

    pdf = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        text_layer = "\n".join(page.get_text() for page in pdf).strip()
        if len(text_layer) >= _MIN_TEXT_LAYER_LENGTH:
            # A real text layer exists -- PDF text extraction has no OCR
            # confidence score to report.
            return text_layer, None

        # Scanned PDF with no usable text layer: render each page to an
        # image and OCR it.
        ocr_texts: list[str] = []
        confidences: list[float] = []
        for page in pdf:
            pixmap = page.get_pixmap(dpi=_PDF_RENDER_DPI)
            png_bytes = pixmap.tobytes("png")
            result = await ocr_engine.extract(file_bytes=png_bytes, mime_type="image/png")
            if result.raw_text:
                ocr_texts.append(result.raw_text)
            if result.confidence is not None:
                confidences.append(result.confidence)

        combined_text = "\n".join(ocr_texts).strip()
        avg_confidence = round(sum(confidences) / len(confidences), 3) if confidences else None
        return combined_text, avg_confidence
    finally:
        pdf.close()
