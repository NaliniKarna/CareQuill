import uuid
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report_share_link import ReportShareLink


class ReportShareLinkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, **fields) -> ReportShareLink:
        link = ReportShareLink(**fields)
        self.session.add(link)
        await self.session.flush()
        return link

    async def list_for_patient(
        self, patient_id: uuid.UUID, *, limit: int = 50
    ) -> list[ReportShareLink]:
        result = await self.session.execute(
            select(ReportShareLink)
            .where(ReportShareLink.patient_id == patient_id)
            .order_by(ReportShareLink.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_id_for_patient(
        self, link_id: uuid.UUID, patient_id: uuid.UUID
    ) -> ReportShareLink | None:
        result = await self.session.execute(
            select(ReportShareLink).where(
                ReportShareLink.id == link_id, ReportShareLink.patient_id == patient_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_token_hash(self, token_hash: str) -> ReportShareLink | None:
        result = await self.session.execute(
            select(ReportShareLink).where(ReportShareLink.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def list_with_files_to_purge(
        self, *, now: datetime, limit: int = 200
    ) -> list[ReportShareLink]:
        """Links that are expired or revoked but still hold a snapshot file."""
        result = await self.session.execute(
            select(ReportShareLink)
            .where(
                ReportShareLink.report_storage_path.is_not(None),
                or_(ReportShareLink.expires_at <= now, ReportShareLink.revoked_at.is_not(None)),
            )
            .limit(limit)
        )
        return list(result.scalars().all())
