"""add_ai_providers

Revision ID: add_ai_providers_2026
Revises: add_system_config_2026
Create Date: 2026-04-30 19:30:00.000000

Multi-provider AI configuration table.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'add_ai_providers_2026'
down_revision: Union[str, None] = 'add_system_config_2026'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('ai_provider',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('provider_type', sa.String(length=50), nullable=False, server_default='custom'),
        sa.Column('api_base', sa.String(length=500), nullable=False),
        sa.Column('api_key', sa.Text(), nullable=False, server_default=''),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('max_tokens', sa.Integer(), nullable=False, server_default='4096'),
        sa.Column('temperature', sa.Float(), nullable=False, server_default='0.3'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('ai_provider')
