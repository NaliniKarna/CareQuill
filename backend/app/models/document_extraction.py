from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DocumentExtraction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Raw OCR/AI extraction output for a document. Always a *suggestion*:
    nothing here is treated as verified patient data until a patient
    reviews and approves it into the structured tables (allergies,
    medications, etc.)."""

    __tablename__ = "document_extractions"

    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("medical_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    extracted_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending_review", nullable=False)
    # pending_review | reviewed | dismissed -- every extraction requires patient
    # review no matter its confidence; confidence only informs the UI badge.
