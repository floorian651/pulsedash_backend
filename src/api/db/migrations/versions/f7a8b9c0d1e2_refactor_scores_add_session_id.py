"""refactor scores: rename track_id to music_title, add session_id

Revision ID: f7a8b9c0d1e2
Revises: e5f6a7b8c9d0
Create Date: 2026-05-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("scores", "track_id", new_column_name="music_title")
    op.drop_index("ix_scores_track_id", table_name="scores")
    op.create_index("ix_scores_music_title", "scores", ["music_title"])

    op.add_column("scores", sa.Column("session_id", sa.String(), nullable=True))
    op.create_unique_constraint("uq_scores_session_id", "scores", ["session_id"])
    op.create_index("ix_scores_session_id", "scores", ["session_id"])

    op.alter_column("scores", "created_at", type_=sa.DateTime(timezone=True))
    op.alter_column("game_sessions", "started_at", type_=sa.DateTime(timezone=True))
    op.alter_column("game_sessions", "ended_at", type_=sa.DateTime(timezone=True))
    op.alter_column("jobs", "created_at", type_=sa.DateTime(timezone=True))
    op.alter_column("jobs", "updated_at", type_=sa.DateTime(timezone=True))
    op.alter_column("users", "created_at", type_=sa.DateTime(timezone=True))


def downgrade() -> None:
    op.alter_column("users", "created_at", type_=sa.DateTime())
    op.alter_column("jobs", "updated_at", type_=sa.DateTime())
    op.alter_column("jobs", "created_at", type_=sa.DateTime())
    op.alter_column("game_sessions", "ended_at", type_=sa.DateTime())
    op.alter_column("game_sessions", "started_at", type_=sa.DateTime())
    op.alter_column("scores", "created_at", type_=sa.DateTime())

    op.drop_index("ix_scores_session_id", table_name="scores")
    op.drop_constraint("uq_scores_session_id", "scores")
    op.drop_column("scores", "session_id")

    op.drop_index("ix_scores_music_title", table_name="scores")
    op.create_index("ix_scores_track_id", "scores", ["music_title"])
    op.alter_column("scores", "music_title", new_column_name="track_id")
