"""add FK constraints on music_title

Revision ID: g8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-05-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "g8b9c0d1e2f3"
down_revision: Union[str, None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_game_sessions_music_title",
        "game_sessions", "music",
        ["music_title"], ["title"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_scores_music_title",
        "scores", "music",
        ["music_title"], ["title"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_scores_music_title", "scores", type_="foreignkey")
    op.drop_constraint("fk_game_sessions_music_title", "game_sessions", type_="foreignkey")
