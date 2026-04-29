"""add_preview_html_path

Revision ID: add_preview_html_path_2026
Revises: enable_pgvector_2026
Create Date: 2026-04-30 09:00:00.000000

Add preview_html_path column to document table for LibreOffice HTML preview:
  - Stores MinIO object path for converted HTML content
  - Used by preview-text endpoint to serve rich HTML preview
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_preview_html_path_2026'
down_revision: Union[str, None] = 'enable_pgvector_2026'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('document', sa.Column('preview_html_path', sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column('document', 'preview_html_path')
