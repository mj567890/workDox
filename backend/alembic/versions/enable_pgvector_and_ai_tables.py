"""enable_pgvector_and_ai_tables

Revision ID: enable_pgvector_2026
Revises: add_extracted_text_2026
Create Date: 2026-04-29 14:00:00.000000

Enable pgvector extension and create AI/RAG tables:
  - CREATE EXTENSION vector
  - Add embedding (Vector 768) column to document
  - Create document_chunk table (with embedding + IVFFlat index)
  - Create ai_conversation table
  - Create ai_message table
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'enable_pgvector_2026'
down_revision: Union[str, None] = 'add_extracted_text_2026'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2. Add embedding column to document table
    op.add_column('document', sa.Column('embedding', Vector(768), nullable=True))
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_document_embedding "
        "ON document USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    # 3. Create document_chunk table
    op.create_table(
        'document_chunk',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), sa.ForeignKey('document.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(768), nullable=True),
        sa.Column('token_count', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id', 'chunk_index', name='uq_doc_chunk_idx'),
    )
    op.create_index('idx_document_chunk_doc_id', 'document_chunk', ['document_id'])
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_document_chunk_embedding "
        "ON document_chunk USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    # 4. Create ai_conversation table
    op.create_table(
        'ai_conversation',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('title', sa.String(200), server_default='New Chat'),
        sa.Column('document_id', sa.Integer(), sa.ForeignKey('document.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_ai_conversation_user_id', 'ai_conversation', ['user_id'])

    # 5. Create ai_message table
    op.create_table(
        'ai_message',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), sa.ForeignKey('ai_conversation.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('sources', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_ai_message_conv_id', 'ai_message', ['conversation_id'])


def downgrade() -> None:
    op.drop_table('ai_message')
    op.drop_table('ai_conversation')
    op.drop_table('document_chunk')
    op.drop_index('idx_document_embedding', table_name='document')
    op.drop_column('document', 'embedding')
