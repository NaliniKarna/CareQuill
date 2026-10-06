"""provenance columns and composite performance indexes

Revision ID: b7c1d2e3f4a5
Revises: a39b467114ed
Create Date: 2026-10-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b7c1d2e3f4a5'
down_revision: Union[str, None] = 'a39b467114ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PROVENANCE_TABLES = ("medications", "allergies", "medical_conditions")


def upgrade() -> None:
    # --- provenance: where did this record come from? ------------------
    for table in _PROVENANCE_TABLES:
        op.add_column(
            table,
            sa.Column("source", sa.String(length=30), server_default="manual", nullable=False),
        )
        op.add_column(
            table,
            sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.create_index(
            op.f(f"ix_{table}_source_document_id"), table, ["source_document_id"], unique=False
        )
        op.create_foreign_key(
            f"fk_{table}_source_document_id",
            table,
            "medical_documents",
            ["source_document_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # --- composite indexes for the "my newest X" list queries ----------
    op.create_index(
        "ix_medical_documents_patient_created", "medical_documents", ["patient_id", "created_at"]
    )
    op.create_index("ix_appointments_patient_date", "appointments", ["patient_id", "appointment_date"])
    op.create_index("ix_notifications_patient_read", "notifications", ["patient_id", "is_read"])
    op.create_index("ix_ai_summaries_patient_created", "ai_summaries", ["patient_id", "created_at"])
    op.create_index(
        "ix_health_snapshots_patient_created", "health_snapshots", ["patient_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_health_snapshots_patient_created", table_name="health_snapshots")
    op.drop_index("ix_ai_summaries_patient_created", table_name="ai_summaries")
    op.drop_index("ix_notifications_patient_read", table_name="notifications")
    op.drop_index("ix_appointments_patient_date", table_name="appointments")
    op.drop_index("ix_medical_documents_patient_created", table_name="medical_documents")

    for table in reversed(_PROVENANCE_TABLES):
        op.drop_constraint(f"fk_{table}_source_document_id", table, type_="foreignkey")
        op.drop_index(op.f(f"ix_{table}_source_document_id"), table_name=table)
        op.drop_column(table, "source_document_id")
        op.drop_column(table, "source")
