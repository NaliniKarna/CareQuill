from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class JournalEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A private, patient-written daily journal entry.

    Journal text is never read by AI, never added to the health snapshot and
    never included in shared reports -- it only ever leaves the app through
    the patient's own account export.
    """

    __tablename__ = "journal_entries"
    __table_args__ = (
        Index("ix_journal_entries_patient_date", "patient_id", "entry_date"),
        CheckConstraint(
            "mood IS NULL OR (mood >= 1 AND mood <= 5)", name="ck_journal_entries_mood_range"
        ),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    # 1 (very low) .. 5 (very good); optional.
    mood: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
