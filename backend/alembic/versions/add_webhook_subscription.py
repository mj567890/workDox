"""add_webhook_subscription

Revision ID: add_webhook_subscription_2026
Revises: add_document_review_2026
Create Date: 2026-04-28 15:00:00.000000

Add webhook_subscription table for event-based webhook notifications.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'add_webhook_subscription_2026'
down_revision: Union[str, None] = 'add_document_review_2026'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'webhook_subscription',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('url', sa.String(length=1000), nullable=False),
        sa.Column('secret', sa.String(length=128), nullable=False),
        sa.Column('events', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_status', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_webhook_user', 'webhook_subscription', ['user_id'])


def downgrade() -> None:
    op.drop_table('webhook_subscription')
