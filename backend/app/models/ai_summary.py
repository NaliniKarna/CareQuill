from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AISummary(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """AI-assisted summary generated from a health snapshot. Always requires
    explicit patient review before it is considered "verified" and eligible
    to be shared with a doctor."""

    __tablename__ = "ai_summaries"
    __table_args__ = (Index("ix_ai_summaries_patient_created", "patient_id", "created_at"),)

    patient_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    health_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("health_snapshots.id", ondelete="SET NULL"),
        nullable=True,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Patient-edited version of `summary_text`, kept separate so the
    # original AI-generated draft is always preserved alongside whatever
    # the patient chose to change. `AISummaryService.share()` sends this
    # when set, falling back to `summary_text` otherwise -- never the raw
    # draft once the patient has edited it.
    edited_summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    structured_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending_review", nullable=False)
    # pending_review | reviewed | shared | outdated (superseded by a newer
    # health snapshot -- set by HealthSnapshotService.generate(), never by hand)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
