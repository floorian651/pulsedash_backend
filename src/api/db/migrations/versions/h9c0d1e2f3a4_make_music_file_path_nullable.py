"""make music.file_path nullable

Revision ID: h9c0d1e2f3a4
Revises: g8b9c0d1e2f3
Create Date: 2026-05-06 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "h9c0d1e2f3a4"
down_revision = "g8b9c0d1e2f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("music", "file_path", existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    op.alter_column("music", "file_path", existing_type=sa.String(), nullable=False)
