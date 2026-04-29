"""add_document_review

Revision ID: add_document_review_2026
Revises: add_sla_fields_2026
Create Date: 2026-04-28 14:00:00.000000

Add document_review table for multi-level document approval workflow:
  - document_review: review records with reviewer, level, status, comment
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_document_review_2026'
down_revision: Union[str, None] = 'add_sla_fields_2026'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'document_review',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('document_id', sa.Integer(), sa.ForeignKey('document.id'), nullable=False),
        sa.Column('review_level', sa.Integer(), nullable=False),
        sa.Column('reviewer_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id', 'review_level', name='uq_doc_review_level'),
    )
    op.create_index('idx_document_review_doc', 'document_review', ['document_id'])
    op.create_index('idx_document_review_reviewer', 'document_review', ['reviewer_id'])


def downgrade() -> None:
    op.drop_table('document_review')
