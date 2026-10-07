"""document recovery attempts

Revision ID: d9e3f5a7b2c4
Revises: c8d2e4f6a1b3
Create Date: 2026-10-07 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d9e3f5a7b2c4"
down_revision: Union[str, None] = "c8d2e4f6a1b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "medical_documents",
        sa.Column("recovery_attempts", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("medical_documents", "recovery_attempts")
