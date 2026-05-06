"""add document.summary column for AI-generated summaries

Revision ID: add_document_summary
Revises: add_ai_providers_2026
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_document_summary_2026'
down_revision: str | None = 'add_ai_providers_2026'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('document', sa.Column('summary', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('document', 'summary')
