from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class HealthSnapshot(UUIDPrimaryKeyMixin, Base):
    """An immutable, versioned point-in-time snapshot of a patient's
    verified health state (conditions, medications, allergies, recent
    events), derived from the structured tables. AI summaries are generated
    from a specific snapshot version, so a summary can always be traced back
    to exactly the verified data it was built from."""

    __tablename__ = "health_snapshots"
    __table_args__ = (Index("ix_health_snapshots_patient_created", "patient_id", "created_at"),)

    patient_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
