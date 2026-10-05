from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DoctorContact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A doctor as a saved contact belonging to a patient. Doctors never have
    their own account/login in the MVP; this is purely patient-owned
    address-book data."""

    __tablename__ = "doctor_contacts"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    specialization: Mapped[str | None] = mapped_column(String(150), nullable=True)
    clinic_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
