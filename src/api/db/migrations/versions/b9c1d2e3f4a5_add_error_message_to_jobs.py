"""add error_message to jobs

Revision ID: b9c1d2e3f4a5
Revises: 6ea784f51a59
Create Date: 2026-04-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b9c1d2e3f4a5"
down_revision: Union[str, None] = "6ea784f51a59"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("error_message", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "error_message")
