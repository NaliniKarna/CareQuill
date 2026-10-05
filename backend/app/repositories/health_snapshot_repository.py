import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health_snapshot import HealthSnapshot


class HealthSnapshotRepository:
    """`HealthSnapshot` rows are immutable, append-only history: this
    repository deliberately has no `update` or `delete` method -- never add
    one, per the project's "AI/derived output is never silently rewritten"
    rule applied to snapshots too."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, *, patient_id: uuid.UUID, version: int, snapshot_data: dict
    ) -> HealthSnapshot:
        snapshot = HealthSnapshot(
            patient_id=patient_id, version=version, snapshot_data=snapshot_data
        )
        self.session.add(snapshot)
        await self.session.flush()
        return snapshot

    async def get_latest(self, patient_id: uuid.UUID) -> HealthSnapshot | None:
        result = await self.session.execute(
            select(HealthSnapshot)
            .where(HealthSnapshot.patient_id == patient_id)
            .order_by(HealthSnapshot.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_versions_for_patient(self, patient_id: uuid.UUID) -> list[HealthSnapshot]:
        result = await self.session.execute(
            select(HealthSnapshot)
            .where(HealthSnapshot.patient_id == patient_id)
            .order_by(HealthSnapshot.version.desc())
        )
        return list(result.scalars().all())

    async def get_by_id_for_patient(
        self, snapshot_id: uuid.UUID, patient_id: uuid.UUID
    ) -> HealthSnapshot | None:
        result = await self.session.execute(
            select(HealthSnapshot).where(
                HealthSnapshot.id == snapshot_id, HealthSnapshot.patient_id == patient_id
            )
        )
        return result.scalar_one_or_none()
