"""add_extracted_text

Revision ID: add_extracted_text_2026
Revises: add_webhook_subscription_2026
Create Date: 2026-04-29 10:00:00.000000

Add extracted_text column to document table for document intelligence pipeline:
  - Store text extracted from docx/xlsx/pdf/txt files
  - Used by FTS similar document search and category suggestion
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_extracted_text_2026'
down_revision: Union[str, None] = 'add_webhook_subscription_2026'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('document', sa.Column('extracted_text', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('document', 'extracted_text')
