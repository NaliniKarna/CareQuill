from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A persisted, patient-facing in-app notification, created at the
    moment a specific event happens (AI summary ready, document processed,
    report shared, email delivery failure).

    Two other notification types (`appointment_approaching`,
    `medication_reminder`) are deliberately NEVER stored here -- they are
    computed fresh on every read by `NotificationService` from live
    appointment/reminder data, because "due within 48 hours" is a fact
    about the clock, not a one-time event. See that service's docstring."""

    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_patient_read", "patient_id", "is_read"),)

    patient_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    # appointment_approaching | medication_reminder | ai_summary_ready |
    # document_processed | report_shared | email_failure
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(String(1000), nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    related_resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
