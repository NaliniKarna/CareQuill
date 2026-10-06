"""journal entries

Revision ID: c8d2e4f6a1b3
Revises: b7c1d2e3f4a5
Create Date: 2026-10-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c8d2e4f6a1b3"
down_revision: Union[str, None] = "b7c1d2e3f4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "journal_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("mood", sa.SmallInteger(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("mood IS NULL OR (mood >= 1 AND mood <= 5)", name="ck_journal_entries_mood_range"),
        sa.ForeignKeyConstraint(["patient_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_journal_entries_patient_id"), "journal_entries", ["patient_id"], unique=False)
    op.create_index("ix_journal_entries_patient_date", "journal_entries", ["patient_id", "entry_date"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_journal_entries_patient_date", table_name="journal_entries")
    op.drop_index(op.f("ix_journal_entries_patient_id"), table_name="journal_entries")
    op.drop_table("journal_entries")
