"""Shared column mixins so every table gets a UUID PK and timezone-aware
timestamps consistently, per the project's database design rules."""
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(UTC)


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class TimestampMixin:
    # `server_default` keeps the DB self-consistent for rows inserted
    # outside the ORM; the client-side `default`/`onupdate` populate the
    # value on the in-memory object immediately, so it's available for
    # response serialization straight after flush without an extra async
    # refresh round-trip (which would otherwise raise MissingGreenlet when
    # accessed from Pydantic's synchronous model_validate).
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=_utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )
