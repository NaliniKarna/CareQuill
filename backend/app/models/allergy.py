from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Allergy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "allergies"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    severity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reaction: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Where this record came from: typed in by the patient ("manual") or
    # added by the patient after reviewing an AI/OCR suggestion from one of
    # their uploaded documents ("document_extraction"). The patient always
    # makes the final entry - nothing is ever written automatically.
    source: Mapped[str] = mapped_column(
        String(30), default="manual", server_default="manual", nullable=False
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("medical_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
