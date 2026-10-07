"""report share links (QR code sharing)

Revision ID: e1f2a3b4c5d6
Revises: d9e3f5a7b2c4
Create Date: 2026-10-07 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d9e3f5a7b2c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "report_share_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("recipient_label", sa.String(length=200), nullable=True),
        sa.Column("patient_name", sa.String(length=200), nullable=False),
        sa.Column("report_name", sa.String(length=200), nullable=False),
        sa.Column("included_sections", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("document_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("report_storage_path", sa.String(length=500), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("view_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_report_share_links_patient_id", "report_share_links", ["patient_id"])
    op.create_index(
        "ix_report_share_links_patient_created", "report_share_links", ["patient_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_report_share_links_patient_created", table_name="report_share_links")
    op.drop_index("ix_report_share_links_patient_id", table_name="report_share_links")
    op.drop_table("report_share_links")
