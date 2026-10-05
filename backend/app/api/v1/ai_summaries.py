import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.db import get_db
from app.models.user import User
from app.schemas.ai_summary import (
    AISummaryEditRequest,
    AISummaryGenerateRequest,
    AISummaryRead,
    AISummaryShareRequest,
    EmailLogRead,
)
from app.services.ai_summary_service import AISummaryService

router = APIRouter(prefix="/ai-summaries", tags=["ai-summaries"])


@router.post("/generate", response_model=AISummaryRead, status_code=201)
async def generate_ai_summary(
    payload: AISummaryGenerateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = AISummaryService(session)
    summary = await service.generate(patient_id=current_user.id, data=payload)
    return AISummaryRead.model_validate(summary)


@router.get("", response_model=list[AISummaryRead])
async def list_ai_summaries(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = AISummaryService(session)
    summaries = await service.list(patient_id=current_user.id)
    return [AISummaryRead.model_validate(s) for s in summaries]


@router.get("/{summary_id}", response_model=AISummaryRead)
async def get_ai_summary(
    summary_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = AISummaryService(session)
    summary = await service.get(patient_id=current_user.id, summary_id=summary_id)
    return AISummaryRead.model_validate(summary)


@router.patch("/{summary_id}", response_model=AISummaryRead)
async def edit_ai_summary(
    summary_id: uuid.UUID,
    payload: AISummaryEditRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = AISummaryService(session)
    summary = await service.save_edit(
        patient_id=current_user.id,
        summary_id=summary_id,
        edited_summary_text=payload.edited_summary_text,
    )
    return AISummaryRead.model_validate(summary)


@router.post("/{summary_id}/confirm", response_model=AISummaryRead)
async def confirm_ai_summary(
    summary_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = AISummaryService(session)
    summary = await service.confirm_review(patient_id=current_user.id, summary_id=summary_id)
    return AISummaryRead.model_validate(summary)


@router.post("/{summary_id}/share", response_model=EmailLogRead)
async def share_ai_summary(
    summary_id: uuid.UUID,
    payload: AISummaryShareRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = AISummaryService(session)
    email_log = await service.share(
        patient_id=current_user.id,
        summary_id=summary_id,
        doctor_contact_id=payload.doctor_contact_id,
    )
    return EmailLogRead.model_validate(email_log)
