from __future__ import annotations

import uuid
from datetime import time

from sqlalchemy import Boolean, ForeignKey, String, Time
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class MedicationReminder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A patient-defined reminder for taking a medication. No push
    notifications are sent -- these are records the dashboard/frontend reads
    to show "reminders due today"."""

    __tablename__ = "medication_reminders"

    medication_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("medications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Denormalized so reminder queries/IDOR checks never need to join through
    # medications to find the owning patient.
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reminder_time: Mapped[time] = mapped_column(Time, nullable=False)
    days_of_week: Mapped[str] = mapped_column(String(50), nullable=False)
    # "daily" or a comma-separated subset of mon,tue,wed,thu,fri,sat,sun
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
