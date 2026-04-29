"""add_fts_indexes

Revision ID: a8c3f1d5e2b9
Revises: 935bfb869fd2
Create Date: 2026-04-28 06:30:00.000000

Add GIN index for full-text search on the matter table.
The document table already has idx_document_search from the initial migration.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8c3f1d5e2b9'
down_revision: Union[str, None] = '935bfb869fd2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add GIN index on matter table for full-text search across title, matter_no, and description
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_matter_fts ON matter "
        "USING GIN(to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(matter_no,'') || ' ' || coalesce(description,'')))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_matter_fts")
