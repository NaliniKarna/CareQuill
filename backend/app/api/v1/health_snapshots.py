import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.db import get_db
from app.core.exceptions import NotFoundError
from app.models.user import User
from app.schemas.health_snapshot import HealthSnapshotRead, HealthSnapshotVersionRead
from app.services.health_snapshot_service import HealthSnapshotService

router = APIRouter(prefix="/health-snapshots", tags=["health-snapshots"])


@router.post("/generate", response_model=HealthSnapshotRead, status_code=201)
async def generate_health_snapshot(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = HealthSnapshotService(session)
    snapshot = await service.generate(patient_id=current_user.id)
    return HealthSnapshotRead.model_validate(snapshot)


@router.get("", response_model=list[HealthSnapshotVersionRead])
async def list_health_snapshots(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = HealthSnapshotService(session)
    snapshots = await service.list_versions(patient_id=current_user.id)
    return [HealthSnapshotVersionRead.model_validate(s) for s in snapshots]


@router.get("/latest", response_model=HealthSnapshotRead)
async def get_latest_health_snapshot(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = HealthSnapshotService(session)
    snapshot = await service.get_latest(patient_id=current_user.id)
    if snapshot is None:
        raise NotFoundError("No health snapshot has been generated yet.")
    return HealthSnapshotRead.model_validate(snapshot)


@router.get("/{snapshot_id}", response_model=HealthSnapshotRead)
async def get_health_snapshot(
    snapshot_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = HealthSnapshotService(session)
    snapshot = await service.get_by_id(patient_id=current_user.id, snapshot_id=snapshot_id)
    if snapshot is None:
        raise NotFoundError("Health snapshot not found.")
    return HealthSnapshotRead.model_validate(snapshot)
