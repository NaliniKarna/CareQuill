from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class MedicalDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Metadata for an uploaded medical document. The original file is kept
    unmodified in storage (see app.storage); `stored_filename` is a
    server-generated name, never the user-supplied one, to prevent path
    traversal and filename-based attacks."""

    __tablename__ = "medical_documents"
    __table_args__ = (Index("ix_medical_documents_patient_created", "patient_id", "created_at"),)

    patient_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    visit_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    doctor_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    hospital_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ocr_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    # pending | processing | completed | failed | skipped
    processing_status: Mapped[str] = mapped_column(String(30), default="uploaded", nullable=False)
    # uploaded | processing | processed | failed
    # How many times startup recovery has re-queued this document. Caps the
    # retries so a document that crashes the worker cannot restart-loop the
    # server forever. Reset when the patient asks for a reprocess.
    recovery_attempts: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
