"""add_system_config

Revision ID: add_system_config_2026
Revises: remove_legacy_2026
Create Date: 2026-04-30 19:00:00.000000

Key-value system configuration table for runtime settings (AI params, etc.)
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'add_system_config_2026'
down_revision: Union[str, None] = 'remove_legacy_2026'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('system_config',
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Text(), nullable=False, server_default=''),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('key'),
    )


def downgrade() -> None:
    op.drop_table('system_config')
