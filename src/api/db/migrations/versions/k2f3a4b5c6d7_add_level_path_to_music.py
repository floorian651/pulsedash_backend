"""add level_path to music

Revision ID: k2f3a4b5c6d7
Revises: j1e2f3a4b5c6
Create Date: 2026-05-20

"""
from alembic import op
import sqlalchemy as sa

revision = 'k2f3a4b5c6d7'
down_revision = 'j1e2f3a4b5c6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('music', sa.Column('level_path', sa.String(), nullable=True))


def downgrade():
    op.drop_column('music', 'level_path')
