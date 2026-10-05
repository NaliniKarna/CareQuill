from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class TimelineNote(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A freeform, patient-authored note attached to a date on the health
    timeline. Always tagged PATIENT_PROVIDED -- never AI-derived."""

    __tablename__ = "timeline_notes"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    note_text: Mapped[str] = mapped_column(Text, nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
