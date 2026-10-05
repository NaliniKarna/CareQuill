from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Kept in one place so the model default and the service/schema defaults
# (app.services.preference_service) can never drift apart.
DEFAULT_NOTIFICATION_PREFS: dict[str, bool] = {
    "appointment_reminders": True,
    "medication_reminders": True,
    "ai_summary_ready": True,
    "document_processed": True,
    "report_shared": True,
    "email_failures": True,
}


class UserPreference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Per-user settings. `data_sharing_consent` is the one privacy setting
    that is functionally meaningful in this app: whether newly uploaded
    documents may be auto-processed by OCR/AI at all (see
    `DocumentProcessingService`, which skips OCR entirely -- leaving
    `ocr_status="skipped"` -- for a patient who has turned this off)."""

    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    notification_prefs: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=lambda: dict(DEFAULT_NOTIFICATION_PREFS)
    )
    data_sharing_consent: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
