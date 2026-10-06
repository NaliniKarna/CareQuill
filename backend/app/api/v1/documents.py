import io
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.db import get_db
from app.core.exceptions import ValidationAppError
from app.core.rate_limit import ai_rate_limit, upload_rate_limit
from app.models.user import User
from app.schemas.document_extraction import (
    DocumentExplanationRead,
    DocumentExtractionRead,
    DocumentExtractionStatusUpdate,
)
from app.schemas.medical_document import (
    MedicalDocumentListResponse,
    MedicalDocumentRead,
    MedicalDocumentUploadForm,
)
from app.services.document_processing_service import process_document
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["medical-documents"])

_MAX_LIMIT = 100


@router.post(
    "",
    response_model=MedicalDocumentRead,
    status_code=201,
    dependencies=[Depends(upload_rate_limit)],
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    category: str | None = Form(None),
    visit_date: str | None = Form(None),
    doctor_name: str | None = Form(None),
    hospital_name: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    try:
        form = MedicalDocumentUploadForm(
            title=title,
            category=category,  # type: ignore[arg-type]
            visit_date=visit_date,  # type: ignore[arg-type]
            doctor_name=doctor_name,
            hospital_name=hospital_name,
        )
    except Exception as exc:  # pydantic.ValidationError
        raise ValidationAppError("Invalid document metadata.", details=str(exc)) from exc

    file_bytes = await file.read()
    if not file.filename:
        raise ValidationAppError("A filename is required.")

    service = DocumentService(session)
    document = await service.upload(
        patient_id=current_user.id,
        file_bytes=file_bytes,
        original_filename=file.filename,
        form=form,
    )
    # OCR/entity extraction runs after the response is sent -- never block
    # the upload on it.
    background_tasks.add_task(process_document, document.id)
    return MedicalDocumentRead.model_validate(document)


@router.get("", response_model=MedicalDocumentListResponse)
async def list_documents(
    category: str | None = Query(default=None),
    processing_status: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=_MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = DocumentService(session)
    items, total = await service.list(
        patient_id=current_user.id,
        category=category,
        processing_status=processing_status,
        q=q,
        limit=limit,
        offset=offset,
    )
    return MedicalDocumentListResponse(
        items=[MedicalDocumentRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{document_id}", response_model=MedicalDocumentRead)
async def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = DocumentService(session)
    document = await service.get(patient_id=current_user.id, document_id=document_id)
    return MedicalDocumentRead.model_validate(document)


@router.get("/{document_id}/download")
async def download_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = DocumentService(session)
    document, content = await service.get_file_bytes(
        patient_id=current_user.id, document_id=document_id
    )
    headers = {
        "Content-Disposition": f'attachment; filename="{document.original_filename}"'
    }
    return StreamingResponse(
        io.BytesIO(content), media_type=document.mime_type, headers=headers
    )


@router.get("/{document_id}/preview")
async def preview_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Same authorized bytes as /download, but `inline` so the in-app viewer
    can show an X-ray / scan / PDF. The frontend fetches it with the bearer
    token and renders a blob URL (never a public storage URL). The strict
    CSP + nosniff stop the browser executing anything embedded in a file."""
    service = DocumentService(session)
    document, content = await service.get_file_bytes(
        patient_id=current_user.id, document_id=document_id
    )
    headers = {
        "Content-Disposition": f'inline; filename="{document.original_filename}"',
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": (
            "default-src 'none'; img-src data:; style-src 'unsafe-inline'; sandbox"
        ),
        "Cache-Control": "private, no-store",
    }
    return StreamingResponse(
        io.BytesIO(content), media_type=document.mime_type, headers=headers
    )


@router.post(
    "/{document_id}/reprocess",
    response_model=MedicalDocumentRead,
    status_code=202,
    dependencies=[Depends(upload_rate_limit)],
)
async def reprocess_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Run OCR/extraction again on an existing upload (does not touch the
    stored original)."""
    service = DocumentService(session)
    document = await service.reprocess(patient_id=current_user.id, document_id=document_id)
    background_tasks.add_task(process_document, document.id)
    return MedicalDocumentRead.model_validate(document)


@router.post(
    "/{document_id}/explain",
    response_model=DocumentExplanationRead,
    dependencies=[Depends(ai_rate_limit)],
)
async def explain_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """AI plain-language explanation of the document's wording. Explicit
    patient action; stored with the extraction. Never a diagnosis."""
    service = DocumentService(session)
    explanation = await service.explain(patient_id=current_user.id, document_id=document_id)
    return DocumentExplanationRead.model_validate(explanation)


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = DocumentService(session)
    await service.delete(patient_id=current_user.id, document_id=document_id)


@router.get("/{document_id}/extraction", response_model=DocumentExtractionRead)
async def get_document_extraction(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = DocumentService(session)
    extraction = await service.get_extraction(
        patient_id=current_user.id, document_id=document_id
    )
    return DocumentExtractionRead.model_validate(extraction)


@router.patch("/{document_id}/extraction", response_model=DocumentExtractionRead)
async def update_document_extraction_status(
    document_id: uuid.UUID,
    payload: DocumentExtractionStatusUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Marks the extraction reviewed/dismissed. Never writes AI-suggested
    values into allergies/medications/conditions -- see
    `DocumentExtractionStatusUpdate`'s docstring."""
    service = DocumentService(session)
    extraction = await service.update_extraction_status(
        patient_id=current_user.id, document_id=document_id, data=payload
    )
    return DocumentExtractionRead.model_validate(extraction)
