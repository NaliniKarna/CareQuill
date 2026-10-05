from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class EmailLog(UUIDPrimaryKeyMixin, Base):
    """An append-only record of every email sent on a patient's behalf (an
    AI summary share or a full health report share). `doctor_name`,
    `appointment_date` and `appointment_reason` are deliberately
    denormalized (copied at send time) rather than looked up live through
    `appointment_id`/a doctor reference -- this is a *history* log, so it
    must keep reading correctly even if the appointment is later edited/
    cancelled or the doctor contact is deleted."""

    __tablename__ = "email_logs"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
    )
    doctor_email: Mapped[str] = mapped_column(String(320), nullable=False)
    doctor_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    appointment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    appointment_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    subject: Mapped[str] = mapped_column(String(300), nullable=False)
    # Human-readable label for what was sent, e.g. "MedQueue AI Health
    # Summary — 2026-09-25". Null for the older AI-summary-only share flow.
    report_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # Which sections/flags were included in a health-report share, recorded
    # for the patient's own history view. Never contains document/summary
    # text -- see HealthReportService._compute_included_sections.
    included_sections: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)  # sent | failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
