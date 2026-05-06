"""add unique constraint on tag.name to prevent duplicate tags

Revision ID: add_tag_name_unique_2026
Revises: add_document_summary_2026
Create Date: 2026-05-06
"""
from alembic import op
import sqlalchemy as sa


revision: str = 'add_tag_name_unique_2026'
down_revision: str | None = 'add_document_summary_2026'
branch_labels = None
depends_on = None


def upgrade():
    # Clean up any existing duplicate tags before adding unique constraint.
    # Keep the oldest tag for each duplicate name and reassign documents.
    op.execute("""
        WITH duplicates AS (
            SELECT name, MIN(id) AS keep_id
            FROM tag
            GROUP BY name
            HAVING COUNT(*) > 1
        ),
        to_delete AS (
            SELECT t.id
            FROM tag t
            JOIN duplicates d ON t.name = d.name
            WHERE t.id != d.keep_id
        )
        UPDATE document_tag dt
        SET tag_id = d.keep_id
        FROM to_delete td
        JOIN tag t ON t.id = td.id
        JOIN duplicates d ON t.name = d.name
        WHERE dt.tag_id = td.id;
    """)
    op.execute("""
        WITH duplicates AS (
            SELECT name, MIN(id) AS keep_id
            FROM tag
            GROUP BY name
            HAVING COUNT(*) > 1
        ),
        to_delete AS (
            SELECT t.id
            FROM tag t
            JOIN duplicates d ON t.name = d.name
            WHERE t.id != d.keep_id
        )
        DELETE FROM tag
        WHERE id IN (SELECT id FROM to_delete);
    """)
    op.create_unique_constraint('uq_tag_name', 'tag', ['name'])


def downgrade():
    op.drop_constraint('uq_tag_name', 'tag', type_='unique')
