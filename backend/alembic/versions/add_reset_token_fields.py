"""add reset_token_hash and reset_token_expires columns to user table for password reset

Revision ID: add_reset_token_fields_2026
Revises: add_tag_name_unique_2026
Create Date: 2026-05-11
"""
from alembic import op
import sqlalchemy as sa

revision: str = 'add_reset_token_fields_2026'
down_revision: str | None = 'add_tag_name_unique_2026'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('user', sa.Column('reset_token_hash', sa.String(255), nullable=True))
    op.add_column('user', sa.Column('reset_token_expires', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('user', 'reset_token_expires')
    op.drop_column('user', 'reset_token_hash')
