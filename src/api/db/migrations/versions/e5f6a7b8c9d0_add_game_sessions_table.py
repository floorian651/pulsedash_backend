"""add game sessions table

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "game_sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("music_title", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("final_score", sa.Integer(), nullable=True),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_game_sessions_user_id", "game_sessions", ["user_id"])
    op.create_index("ix_game_sessions_music_title", "game_sessions", ["music_title"])


def downgrade() -> None:
    op.drop_index("ix_game_sessions_music_title", "game_sessions")
    op.drop_index("ix_game_sessions_user_id", "game_sessions")
    op.drop_table("game_sessions")
