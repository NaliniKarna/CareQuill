import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.db import get_db
from app.models.user import User
from app.schemas.journal import (
    JournalEntryCreate,
    JournalEntryRead,
    JournalEntryUpdate,
    JournalListResponse,
)
from app.services.journal_service import JournalService

router = APIRouter(prefix="/journal", tags=["journal"])


@router.post("", response_model=JournalEntryRead, status_code=201)
async def create_entry(
    payload: JournalEntryCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    entry = await JournalService(session).create(patient_id=current_user.id, data=payload)
    return JournalEntryRead.model_validate(entry)


@router.get("", response_model=JournalListResponse)
async def list_entries(
    date_from: date | None = None,
    date_to: date | None = None,
    q: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    items, total = await JournalService(session).list(
        patient_id=current_user.id,
        date_from=date_from,
        date_to=date_to,
        q=q,
        limit=limit,
        offset=offset,
    )
    return JournalListResponse(
        items=[JournalEntryRead.model_validate(i) for i in items], total=total
    )


@router.get("/{entry_id}", response_model=JournalEntryRead)
async def get_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    entry = await JournalService(session).get(patient_id=current_user.id, entry_id=entry_id)
    return JournalEntryRead.model_validate(entry)


@router.put("/{entry_id}", response_model=JournalEntryRead)
async def update_entry(
    entry_id: uuid.UUID,
    payload: JournalEntryUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    entry = await JournalService(session).update(
        patient_id=current_user.id, entry_id=entry_id, data=payload
    )
    return JournalEntryRead.model_validate(entry)


@router.delete("/{entry_id}", status_code=204)
async def delete_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await JournalService(session).delete(patient_id=current_user.id, entry_id=entry_id)
