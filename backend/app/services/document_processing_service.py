"""
Background OCR + structured-entity-extraction pipeline, kicked off (via
FastAPI `BackgroundTasks`) right after a document upload so the upload
response never blocks on OCR.

Three kinds of upload are handled differently (see also
`app.services.imaging_service` for why):

 * Text documents (PDF with a text layer, scanned PDF, photo of a report):
   text is extracted (OCR where needed), then regex entity extraction runs.
 * Medical images (category xray / mri / ct_scan, image file): NOT run through
   text extraction as if they were reports. Only burned-in annotations are
   read; the image is never interpreted.
 * Images with no readable text (a photo, an unlabeled scan): reported as
   "no_text" instead of a misleading "completed".

The pipeline has two phases so the patient sees results quickly:
 1. Fast, deterministic phase (OCR + regex). Commits and marks the document
    "processed".
 2. Optional AI phase (LLM extraction / image description). Enriches the same
    extraction in place; any failure leaves phase-1 results untouched.

Each phase runs in its OWN database session (`session_scope`) because a
background task executes after the request's session has closed.

CPU-heavy work (PyMuPDF, Pillow, Tesseract) runs in worker threads: running it
inline in this `async def` would freeze every other request on the server.
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.ai.factory import get_ai_provider
from app.core.config import settings
from app.core.logging import logger
from app.db.session import session_scope
from app.ocr.factory import get_ocr_engine
from app.ocr.interface import OCREngine
from app.repositories.document_extraction_repository import DocumentExtractionRepository
from app.repositories.medical_document_repository import MedicalDocumentRepository
from app.repositories.user_preference_repository import UserPreferenceRepository
from app.services.document_ai_service import (
    document_ai_enabled,
    extract_with_ai,
    merge_ai_into_extracted,
)
from app.services.entity_extraction_service import clean_text, empty_entities, extract_entities
from app.services.imaging_service import (
    NO_TEXT_IMAGE_NOTICE,
    build_imaging_extraction,
    describe_image_with_ai,
    is_imaging_category,
)
from app.services.notification_service import NotificationService
from app.storage.factory import get_storage_backend

_MIN_TEXT_LAYER_LENGTH = 20  # below this, treat a PDF as having no usable text layer
_PDF_RENDER_DPI = 200
_STUCK_AFTER = timedelta(minutes=10)

_SUPPORTED_IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/jpg"}

OCR_OFF_NOTICE = (
    "Automatic text reading (OCR) is switched off on this server, so this "
    "document was stored but nothing was extracted. The original file is "
    "safe and can be viewed or downloaded."
)


@dataclass
class _Phase1Result:
    kind: str  # "text" | "imaging" | "none"
    raw_text: str = ""


async def process_document(document_id: uuid.UUID) -> None:
    """Entry point called from the upload route's BackgroundTasks."""
    try:
        result = await _run_pipeline(document_id)
    except Exception:
        # Full detail server-side only; never surfaced to the patient.
        logger.exception("Document processing failed for document_id=%s", document_id)
        await _mark_failed(document_id)
        return

    if result.kind == "none" or not _ai_phase_wanted():
        return
    try:
        await _run_ai_phase(document_id, result)
    except Exception:
        logger.exception("AI enrichment failed for document_id=%s", document_id)
        await _set_ai_status(document_id, "failed")


def _ai_phase_wanted() -> bool:
    return document_ai_enabled()


# ---------------------------------------------------------------------------
# Phase 1 - deterministic
# ---------------------------------------------------------------------------
async def _run_pipeline(document_id: uuid.UUID) -> _Phase1Result:
    async with session_scope() as session:
        document_repo = MedicalDocumentRepository(session)
        extraction_repo = DocumentExtractionRepository(session)

        document = await document_repo.get_by_id(document_id)
        if document is None:
            return _Phase1Result(kind="none")

        preferences = UserPreferenceRepository(session)
        preference = await preferences.get_by_user_id(document.patient_id)
        if preference is not None and not preference.data_sharing_consent:
            # The patient has opted out of automatic OCR/AI processing --
            # never process this (or any future) upload of theirs until
            # they turn it back on. The file itself is still kept.
            await document_repo.update_status(
                document, ocr_status="skipped", processing_status="processed"
            )
            return _Phase1Result(kind="none")

        await document_repo.update_status(document, processing_status="processing")

        storage = get_storage_backend()
        try:
            file_bytes = await storage.read(storage_path=document.storage_path)
        except FileNotFoundError:
            logger.error("Document %s: file missing from storage during OCR.", document_id)
            await document_repo.update_status(
                document, ocr_status="failed", processing_status="failed"
            )
            return _Phase1Result(kind="none")

        ocr_engine = get_ocr_engine()
        is_image = document.mime_type in _SUPPORTED_IMAGE_MIME_TYPES

        # -- medical images: annotations only, never interpreted ---------------
        if is_image and is_imaging_category(document.category):
            text, confidence, extracted = await build_imaging_extraction(
                file_bytes=file_bytes, mime_type=document.mime_type, ocr_engine=ocr_engine
            )
            extracted["ai_status"] = "pending" if _ai_phase_wanted() else "disabled"
            await _save_extraction(
                extraction_repo, document.id, text, confidence, extracted, status="pending_review"
            )
            await document_repo.update_status(
                document, ocr_status="not_applicable", processing_status="processed"
            )
            await _notify_done(session, document)
            return _Phase1Result(kind="imaging", raw_text=text)

        # -- text documents ------------------------------------------------------
        raw_text, confidence = await _extract_text(
            file_bytes=file_bytes, mime_type=document.mime_type, ocr_engine=ocr_engine
        )

        if raw_text is None:
            # Unsupported mime type for extraction (shouldn't normally
            # happen given upload-time validation, but fail safe).
            await document_repo.update_status(
                document, ocr_status="skipped", processing_status="processed"
            )
            return _Phase1Result(kind="none")

        cleaned = clean_text(raw_text)
        word_count = len(cleaned.split())

        if word_count < settings.ocr_min_words and not ocr_engine.is_real:
            # OCR is switched off and there's no text layer to fall back on:
            # say so honestly rather than reporting a "completed" OCR run.
            extracted = {**empty_entities(), "notice": OCR_OFF_NOTICE, "ai_status": "disabled"}
            await _save_extraction(
                extraction_repo, document.id, "", None, extracted, status="pending_review"
            )
            await document_repo.update_status(
                document, ocr_status="skipped", processing_status="processed"
            )
            return _Phase1Result(kind="none")

        if word_count < settings.ocr_min_words:
            # OCR ran but found (almost) no text: a photo, an unlabeled scan,
            # or an unreadable page.
            extracted = {
                **empty_entities(),
                "notice": NO_TEXT_IMAGE_NOTICE,
                "ai_status": "disabled",
            }
            await _save_extraction(
                extraction_repo, document.id, cleaned, confidence, extracted,
                status="pending_review",
            )
            await document_repo.update_status(
                document, ocr_status="no_text", processing_status="processed"
            )
            await _notify_done(session, document)
            return _Phase1Result(kind="none")

        extracted = extract_entities(cleaned)
        extracted["extraction_method"] = "pattern"
        extracted["ai_status"] = "pending" if _ai_phase_wanted() else "disabled"
        await _save_extraction(
            extraction_repo, document.id, cleaned, confidence, extracted, status="pending_review"
        )
        await document_repo.update_status(
            document, ocr_status="completed", processing_status="processed"
        )
        await _notify_done(session, document)
        return _Phase1Result(kind="text", raw_text=cleaned)


async def _save_extraction(
    repo: DocumentExtractionRepository,
    document_id: uuid.UUID,
    raw_text: str,
    confidence: float | None,
    extracted_data: dict,
    *,
    status: str,
) -> None:
    existing = await repo.get_by_document_id(document_id)
    if existing is None:
        await repo.create(
            document_id=document_id,
            raw_text=raw_text,
            confidence=confidence,
            extracted_data=extracted_data,
            status=status,
        )
    else:
        # Re-processing resets review state: new content needs a new review.
        await repo.update(
            existing,
            raw_text=raw_text,
            confidence=confidence,
            extracted_data=extracted_data,
            status=status,
        )


async def _notify_done(session, document) -> None:
    await NotificationService(session).notify(
        patient_id=document.patient_id,
        type="document_processed",
        title="Document processed",
        body=f"'{document.title}' has finished processing and is ready to review.",
        related_resource_id=document.id,
    )


# ---------------------------------------------------------------------------
# Phase 2 - optional AI enrichment
# ---------------------------------------------------------------------------
async def _run_ai_phase(document_id: uuid.UUID, phase1: _Phase1Result) -> None:
    provider = get_ai_provider()
    if not await provider.is_available():
        await _set_ai_status(document_id, "unavailable")
        return

    model_name = getattr(provider, "model", None) or "ai"
    ai_result = None
    image_description = None

    if phase1.kind == "text":
        parsed = await extract_with_ai(provider=provider, document_text=phase1.raw_text)
        ai_result = parsed
    elif phase1.kind == "imaging" and settings.ai_vision_enabled:
        async with session_scope() as session:
            document = await MedicalDocumentRepository(session).get_by_id(document_id)
            storage_path = document.storage_path if document else None
        if storage_path:
            file_bytes = await get_storage_backend().read(storage_path=storage_path)
            image_description = await describe_image_with_ai(
                provider=provider,
                file_bytes=file_bytes,
                model_name=getattr(provider, "vision_model", model_name),
            )

    async with session_scope() as session:
        repo = DocumentExtractionRepository(session)
        extraction = await repo.get_by_document_id(document_id)
        if extraction is None or extraction.extracted_data is None:
            return
        data = dict(extraction.extracted_data)

        if phase1.kind == "text":
            if ai_result is None:
                data["ai_status"] = "failed"
            else:
                data = merge_ai_into_extracted(data, ai_result)
                data["extraction_method"] = "pattern+ai"
                data["ai_model"] = model_name
                data["ai_status"] = "done"
        else:
            imaging = dict(data.get("imaging") or {})
            imaging["ai_description"] = image_description
            data["imaging"] = imaging
            data["ai_status"] = "done" if image_description else "disabled"

        await repo.update(extraction, extracted_data=data)


async def _set_ai_status(document_id: uuid.UUID, ai_status: str) -> None:
    try:
        async with session_scope() as session:
            repo = DocumentExtractionRepository(session)
            extraction = await repo.get_by_document_id(document_id)
            if extraction is not None and extraction.extracted_data is not None:
                await repo.update(
                    extraction, extracted_data={**extraction.extracted_data, "ai_status": ai_status}
                )
    except Exception:
        logger.exception("Could not record AI status for document %s.", document_id)


# ---------------------------------------------------------------------------
# Failure + recovery
# ---------------------------------------------------------------------------
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


async def recover_stuck_documents() -> int:
    """Called once at startup. Background tasks live in the server process,
    so a restart/crash mid-processing leaves documents stuck on
    "processing" forever. Re-queue them (bounded)."""
    cutoff = datetime.now(UTC) - _STUCK_AFTER
    try:
        async with session_scope() as session:
            stuck = await MedicalDocumentRepository(session).list_stuck(updated_before=cutoff)
            ids = [d.id for d in stuck]
    except Exception:
        logger.exception("Could not look for stuck documents.")
        return 0

    for document_id in ids:
        asyncio.create_task(process_document(document_id))
    if ids:
        logger.warning("Re-queued %d document(s) left unprocessed by a restart.", len(ids))
    return len(ids)


# ---------------------------------------------------------------------------
# Text extraction (blocking libraries run in worker threads)
# ---------------------------------------------------------------------------
async def _extract_text(
    *, file_bytes: bytes, mime_type: str, ocr_engine: OCREngine
) -> tuple[str | None, float | None]:
    if mime_type == "application/pdf":
        return await _extract_pdf_text(file_bytes, ocr_engine)
    if mime_type in _SUPPORTED_IMAGE_MIME_TYPES:
        result = await ocr_engine.extract(file_bytes=file_bytes, mime_type=mime_type)
        return result.raw_text, result.confidence
    return None, None


def _read_pdf_text_layer(file_bytes: bytes) -> str:
    import fitz  # PyMuPDF

    pdf = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        return "\n".join(page.get_text() for page in pdf).strip()
    finally:
        pdf.close()


def _render_pdf_pages(file_bytes: bytes) -> list[bytes]:
    import fitz  # PyMuPDF

    pdf = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        pages: list[bytes] = []
        for index, page in enumerate(pdf):
            if index >= settings.ocr_max_pdf_pages:
                break
            pages.append(page.get_pixmap(dpi=_PDF_RENDER_DPI).tobytes("png"))
        return pages
    finally:
        pdf.close()


async def _extract_pdf_text(
    file_bytes: bytes, ocr_engine: OCREngine
) -> tuple[str, float | None]:
    text_layer = await asyncio.to_thread(_read_pdf_text_layer, file_bytes)
    if len(text_layer) >= _MIN_TEXT_LAYER_LENGTH:
        # A real text layer exists -- PDF text extraction has no OCR
        # confidence score to report.
        return text_layer, None

    if not ocr_engine.is_real:
        return "", None

    # Scanned PDF with no usable text layer: render each page to an image
    # and OCR it (page count capped to bound worst-case CPU time).
    page_images = await asyncio.to_thread(_render_pdf_pages, file_bytes)
    ocr_texts: list[str] = []
    confidences: list[float] = []
    for png_bytes in page_images:
        result = await ocr_engine.extract(file_bytes=png_bytes, mime_type="image/png")
        if result.raw_text:
            ocr_texts.append(result.raw_text)
        if result.confidence is not None:
            confidences.append(result.confidence)

    combined_text = "\n".join(ocr_texts).strip()
    avg_confidence = round(sum(confidences) / len(confidences), 3) if confidences else None
    return combined_text, avg_confidence
