import io
import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Response,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.db import get_db
from app.core.exceptions import ValidationAppError
from app.core.rate_limit import family_claim_rate_limit, upload_rate_limit
from app.models.user import User
from app.schemas.family import (
    FamilyAccessDecision,
    FamilyClaimRequest,
    FamilyDocumentRead,
    FamilyInviteCreated,
    FamilyLinkedToMe,
    FamilyMemberCreate,
    FamilyMemberRead,
    FamilyMemberUpdate,
    FamilyShareLogRead,
    FamilyShareRequest,
)
from app.schemas.medical_document import MedicalDocumentUploadForm
from app.services.document_processing_service import process_document
from app.services.family_service import FamilyService

router = APIRouter(prefix="/family", tags=["family"])


# -- profiles ---------------------------------------------------------------------
@router.get("/members", response_model=list[FamilyMemberRead])
async def list_members(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await FamilyService(session).list_members(manager_id=current_user.id)


@router.post("/members", response_model=FamilyMemberRead, status_code=201)
async def create_member(
    payload: FamilyMemberCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = FamilyService(session)
    member = await service.create_member(manager_id=current_user.id, data=payload)
    return await service.get_member(manager_id=current_user.id, member_id=member.id)


@router.get("/members/{member_id}", response_model=FamilyMemberRead)
async def get_member(
    member_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await FamilyService(session).get_member(
        manager_id=current_user.id, member_id=member_id
    )


@router.patch("/members/{member_id}", response_model=FamilyMemberRead)
async def update_member(
    member_id: uuid.UUID,
    payload: FamilyMemberUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = FamilyService(session)
    await service.update_member(manager_id=current_user.id, member_id=member_id, data=payload)
    return await service.get_member(manager_id=current_user.id, member_id=member_id)


@router.delete("/members/{member_id}", status_code=204)
async def delete_member(
    member_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Removes the profile from your circle (and its stored documents if the
    person has no account). A linked person's own account is never touched."""
    await FamilyService(session).delete_member(manager_id=current_user.id, member_id=member_id)


# -- invite / claim -----------------------------------------------------------------
@router.post("/members/{member_id}/invite", response_model=FamilyInviteCreated, status_code=201)
async def create_invite(
    member_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Creates a one-time code the person enters in their own account. The
    code is shown only once; only its hash is stored."""
    code, expires_at = await FamilyService(session).create_invite(
        manager_id=current_user.id, member_id=member_id
    )
    return FamilyInviteCreated(code=code, expires_at=expires_at)


@router.delete("/members/{member_id}/invite", status_code=204)
async def revoke_invite(
    member_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await FamilyService(session).revoke_invite(manager_id=current_user.id, member_id=member_id)


@router.post(
    "/claim",
    response_model=FamilyLinkedToMe,
    dependencies=[Depends(family_claim_rate_limit)],
)
async def claim_profile(
    payload: FamilyClaimRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Claims a profile with an invite code. The profile's documents move into
    your account; you then choose whether the person who created it keeps
    access."""
    service = FamilyService(session)
    result = await service.claim(user=current_user, code=payload.code)
    for document_id in result.new_document_ids:
        background_tasks.add_task(process_document, document_id)
    linked = await service.list_linked_to_me(user_id=current_user.id)
    return next(item for item in linked if item.id == result.member.id)


# -- the person's own side -------------------------------------------------------------
@router.get("/linked-to-me", response_model=list[FamilyLinkedToMe])
async def list_linked_to_me(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await FamilyService(session).list_linked_to_me(user_id=current_user.id)


@router.post("/linked-to-me/{member_id}/access", response_model=FamilyLinkedToMe)
async def decide_access(
    member_id: uuid.UUID,
    payload: FamilyAccessDecision,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Keep the person who created this profile as a helper, or end their
    access. You can change your mind at any time."""
    return await FamilyService(session).decide_access(
        user_id=current_user.id, member_id=member_id, allow=payload.allow
    )


# -- documents ---------------------------------------------------------------------------
@router.get("/members/{member_id}/documents", response_model=list[FamilyDocumentRead])
async def list_documents(
    member_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await FamilyService(session).list_documents(
        manager_id=current_user.id, member_id=member_id
    )


@router.post(
    "/members/{member_id}/documents",
    response_model=FamilyDocumentRead,
    status_code=201,
    dependencies=[Depends(upload_rate_limit)],
)
async def upload_document(
    member_id: uuid.UUID,
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
            category=category or None,  # type: ignore[arg-type]
            visit_date=visit_date or None,  # type: ignore[arg-type]
            doctor_name=doctor_name or None,
            hospital_name=hospital_name or None,
        )
    except Exception as exc:  # pydantic.ValidationError
        raise ValidationAppError("Invalid document details.", details=str(exc)) from exc
    if not file.filename:
        raise ValidationAppError("A filename is required.")

    document, process_id = await FamilyService(session).upload_document(
        manager_id=current_user.id,
        member_id=member_id,
        file_bytes=await file.read(),
        original_filename=file.filename,
        form=form,
    )
    if process_id is not None:
        # Uploaded into the person's own account: OCR suggestions wait there
        # for the person's review.
        background_tasks.add_task(process_document, process_id)
    return document


def _file_response(file, *, inline: bool) -> StreamingResponse:
    disposition = "inline" if inline else "attachment"
    headers = {"Content-Disposition": f'{disposition}; filename="{file.filename}"'}
    if inline:
        headers.update(
            {
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": (
                    "default-src 'none'; img-src data:; style-src 'unsafe-inline'; sandbox"
                ),
                "Cache-Control": "private, no-store",
            }
        )
    return StreamingResponse(io.BytesIO(file.content), media_type=file.mime_type, headers=headers)


@router.get("/members/{member_id}/documents/{document_id}/download")
async def download_document(
    member_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    file = await FamilyService(session).read_document(
        manager_id=current_user.id, member_id=member_id, document_id=document_id
    )
    return _file_response(file, inline=False)


@router.get("/members/{member_id}/documents/{document_id}/preview")
async def preview_document(
    member_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    file = await FamilyService(session).read_document(
        manager_id=current_user.id, member_id=member_id, document_id=document_id
    )
    return _file_response(file, inline=True)


@router.delete("/members/{member_id}/documents/{document_id}", status_code=204)
async def delete_document(
    member_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await FamilyService(session).delete_document(
        manager_id=current_user.id, member_id=member_id, document_id=document_id
    )
    return Response(status_code=204)


# -- sharing ---------------------------------------------------------------------------------
@router.post("/members/{member_id}/share", response_model=FamilyShareLogRead)
async def share_documents(
    member_id: uuid.UUID,
    payload: FamilyShareRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """The explicit confirmation to send: emails a summary page plus the
    selected original files. Nothing is sent by any other endpoint."""
    return await FamilyService(session).share(
        manager=current_user, member_id=member_id, request=payload
    )


@router.get("/members/{member_id}/shares", response_model=list[FamilyShareLogRead])
async def list_shares(
    member_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await FamilyService(session).list_shares(
        manager_id=current_user.id, member_id=member_id
    )
