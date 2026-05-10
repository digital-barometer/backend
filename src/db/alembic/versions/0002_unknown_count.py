"""add unknown count to analysis metrics

Revision ID: 0002_unknown_count
Revises: 0001_initial_barometer_schema
Create Date: 2026-05-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_unknown_count"
down_revision: Union[str, None] = "0001_initial_barometer_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "analysis_metrics",
        sa.Column("unknown_count", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("analysis_metrics", "unknown_count")
