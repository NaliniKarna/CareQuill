import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.family_member import FamilyDocument, FamilyMember, FamilyShareLog


class FamilyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # -- members ------------------------------------------------------------
    async def create_member(self, *, manager_id: uuid.UUID, **fields) -> FamilyMember:
        member = FamilyMember(manager_id=manager_id, **fields)
        self.session.add(member)
        await self.session.flush()
        return member

    async def get_member_for_manager(
        self, member_id: uuid.UUID, manager_id: uuid.UUID
    ) -> FamilyMember | None:
        result = await self.session.execute(
            select(FamilyMember).where(
                FamilyMember.id == member_id, FamilyMember.manager_id == manager_id
            )
        )
        return result.scalar_one_or_none()

    async def get_member_for_subject(
        self, member_id: uuid.UUID, user_id: uuid.UUID
    ) -> FamilyMember | None:
        result = await self.session.execute(
            select(FamilyMember).where(
                FamilyMember.id == member_id, FamilyMember.linked_user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_manager(self, manager_id: uuid.UUID) -> list[FamilyMember]:
        result = await self.session.execute(
            select(FamilyMember)
            .where(FamilyMember.manager_id == manager_id)
            .order_by(FamilyMember.created_at)
        )
        return list(result.scalars().all())

    async def list_linked_to_user(self, user_id: uuid.UUID) -> list[FamilyMember]:
        result = await self.session.execute(
            select(FamilyMember)
            .where(FamilyMember.linked_user_id == user_id)
            .order_by(FamilyMember.claimed_at)
        )
        return list(result.scalars().all())

    async def count_for_manager(self, manager_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(FamilyMember).where(
                FamilyMember.manager_id == manager_id
            )
        )
        return int(result.scalar_one())

    async def get_by_invite_hash_for_update(self, code_hash: str) -> FamilyMember | None:
        result = await self.session.execute(
            select(FamilyMember)
            .where(FamilyMember.invite_code_hash == code_hash)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def delete_member(self, member: FamilyMember) -> None:
        await self.session.delete(member)
        await self.session.flush()

    # -- documents (profiles without an account) ----------------------------
    async def create_document(self, *, family_member_id: uuid.UUID, **fields) -> FamilyDocument:
        document = FamilyDocument(family_member_id=family_member_id, **fields)
        self.session.add(document)
        await self.session.flush()
        return document

    async def list_documents(self, family_member_id: uuid.UUID) -> list[FamilyDocument]:
        result = await self.session.execute(
            select(FamilyDocument)
            .where(FamilyDocument.family_member_id == family_member_id)
            .order_by(FamilyDocument.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_document(
        self, document_id: uuid.UUID, family_member_id: uuid.UUID
    ) -> FamilyDocument | None:
        result = await self.session.execute(
            select(FamilyDocument).where(
                FamilyDocument.id == document_id,
                FamilyDocument.family_member_id == family_member_id,
            )
        )
        return result.scalar_one_or_none()

    async def count_documents(self, family_member_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(FamilyDocument).where(
                FamilyDocument.family_member_id == family_member_id
            )
        )
        return int(result.scalar_one())

    async def delete_document(self, document: FamilyDocument) -> None:
        await self.session.delete(document)
        await self.session.flush()

    # -- share logs ----------------------------------------------------------
    async def create_share_log(self, **fields) -> FamilyShareLog:
        log = FamilyShareLog(**fields)
        self.session.add(log)
        await self.session.flush()
        return log

    async def list_share_logs(
        self, *, manager_id: uuid.UUID, family_member_id: uuid.UUID, limit: int = 50
    ) -> list[FamilyShareLog]:
        result = await self.session.execute(
            select(FamilyShareLog)
            .where(
                FamilyShareLog.manager_id == manager_id,
                FamilyShareLog.family_member_id == family_member_id,
            )
            .order_by(FamilyShareLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def storage_paths_for_manager(self, manager_id: uuid.UUID) -> list[str]:
        result = await self.session.execute(
            select(FamilyDocument.storage_path)
            .join(FamilyMember, FamilyMember.id == FamilyDocument.family_member_id)
            .where(FamilyMember.manager_id == manager_id)
        )
        return list(result.scalars().all())


