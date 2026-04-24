"""add scores table

Revision ID: c3d4e5f6a7b8
Revises: b9c1d2e3f4a5
Create Date: 2026-04-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b9c1d2e3f4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scores",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("track_id", sa.String(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scores_user_id", "scores", ["user_id"])
    op.create_index("ix_scores_track_id", "scores", ["track_id"])


def downgrade() -> None:
    op.drop_index("ix_scores_track_id", "scores")
    op.drop_index("ix_scores_user_id", "scores")
    op.drop_table("scores")
