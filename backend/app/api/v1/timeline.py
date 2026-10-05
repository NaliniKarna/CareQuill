import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.db import get_db
from app.models.user import User
from app.schemas.timeline import TimelineEntry, TimelineNoteCreate, TimelineNoteRead
from app.services.timeline_note_service import TimelineNoteService
from app.services.timeline_service import TimelineService

router = APIRouter(prefix="/timeline", tags=["timeline"])


@router.get("", response_model=list[TimelineEntry])
async def get_timeline(
    type: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = TimelineService(session)
    return await service.get_timeline(
        patient_id=current_user.id, entry_type=type, date_from=date_from, date_to=date_to
    )


@router.post("/notes", response_model=TimelineNoteRead, status_code=201)
async def create_timeline_note(
    payload: TimelineNoteCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = TimelineNoteService(session)
    note = await service.create(patient_id=current_user.id, data=payload)
    return TimelineNoteRead.model_validate(note)


@router.get("/notes", response_model=list[TimelineNoteRead])
async def list_timeline_notes(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = TimelineNoteService(session)
    notes = await service.list(patient_id=current_user.id)
    return [TimelineNoteRead.model_validate(n) for n in notes]


@router.delete("/notes/{note_id}", status_code=204)
async def delete_timeline_note(
    note_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = TimelineNoteService(session)
    await service.delete(patient_id=current_user.id, note_id=note_id)
