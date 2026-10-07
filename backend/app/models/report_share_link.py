from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ReportShareLink(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A patient-created, time-limited link (shown as a QR code) to one
    health report snapshot and the documents chosen with it.

    Only a SHA-256 hash of the secret token is stored, so a database leak
    does not expose working links. The report PDF is generated once at
    creation (exactly what the patient previewed) and kept in storage until
    the link is revoked or expires.
    """

    __tablename__ = "report_share_links"
    __table_args__ = (Index("ix_report_share_links_patient_created", "patient_id", "created_at"),)

    patient_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    # Display only ("Dr. Anjali Thapa" or None for "anyone").
    recipient_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    patient_name: Mapped[str] = mapped_column(String(200), nullable=False)
    report_name: Mapped[str] = mapped_column(String(200), nullable=False)
    included_sections: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # Snapshot of the document ids the patient chose (as strings).
    document_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # Null once the snapshot file has been removed (revoked/expired).
    report_storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_viewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
