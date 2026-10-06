from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.db import get_db
from app.core.rate_limit import auth_rate_limit, upload_rate_limit
from app.models.user import User
from app.schemas.account import AccountDeleteRequest
from app.services.account_service import AccountService

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/export", dependencies=[Depends(upload_rate_limit)])
async def export_account_data(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Download all of your data (records as JSON + original documents) as a
    ZIP. Only ever returns the caller's own data."""
    content = await AccountService(session).export_zip(user=current_user)
    filename = f"medai-export-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.zip"
    return Response(
        content=content,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-store",
        },
    )


@router.post("/delete", status_code=204, dependencies=[Depends(auth_rate_limit)])
async def delete_account(
    payload: AccountDeleteRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Permanently delete the account and everything in it. Requires the
    password and the word DELETE. Cannot be undone."""
    await AccountService(session).delete_account(
        user=current_user, password=payload.password, confirmation=payload.confirmation
    )
    return Response(status_code=204)
