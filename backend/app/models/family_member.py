from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# link_status values
LINK_UNLINKED = "unlinked"  # a profile the manager keeps for someone without an account
LINK_PENDING = "pending"  # the person claimed it and has not chosen yet; manager has no access
LINK_ACTIVE = "active"  # the person chose to keep the manager as a helper
LINK_ENDED = "ended"  # the person removed the manager's access


class FamilyMember(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A person in a patient's family circle.

    While `link_status` is "unlinked" the manager owns this profile and its
    documents (`family_documents`). Once the person claims it with an invite
    code, their documents move into their own account and the person decides
    whether the manager keeps helper access (see FamilyService)."""

    __tablename__ = "family_members"
    __table_args__ = (
        UniqueConstraint("manager_id", "linked_user_id", name="uq_family_manager_linked"),
        Index("ix_family_members_linked_user", "linked_user_id"),
    )

    manager_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    linked_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    link_status: Mapped[str] = mapped_column(
        String(20), default=LINK_UNLINKED, server_default=LINK_UNLINKED, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    relation: Mapped[str] = mapped_column(String(30), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    blood_group: Mapped[str | None] = mapped_column(String(10), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Only a SHA-256 hash of the invite code is stored.
    invite_code_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    invite_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FamilyDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A file the manager stored for a profile that has no account yet. The
    original file is kept unmodified in storage (see app.storage)."""

    __tablename__ = "family_documents"

    family_member_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("family_members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    visit_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    doctor_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    hospital_name: Mapped[str | None] = mapped_column(String(200), nullable=True)


class FamilyShareLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """History of documents a manager emailed for a family member."""

    __tablename__ = "family_share_logs"

    manager_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    family_member_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("family_members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    recipient_email: Mapped[str] = mapped_column(String(320), nullable=False)
    # Titles only, never file contents.
    document_titles: Mapped[list] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # sent | failed
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
