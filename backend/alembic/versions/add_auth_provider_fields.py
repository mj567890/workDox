"""add_auth_provider_fields

Revision ID: add_auth_provider_2026
Revises: enable_pgvector_and_ai_tables
Create Date: 2026-04-30 14:00:00.000000

Add auth_provider, oauth_provider, oauth_subject columns to user table
for LDAP / OAuth2 / OIDC authentication support.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'add_auth_provider_2026'
down_revision: Union[str, None] = 'enable_pgvector_and_ai_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user', sa.Column('auth_provider', sa.String(20), nullable=False, server_default='local'))
    op.add_column('user', sa.Column('oauth_provider', sa.String(50), nullable=True))
    op.add_column('user', sa.Column('oauth_subject', sa.String(200), nullable=True))
    op.create_unique_constraint('uq_user_oauth_subject', 'user', ['oauth_subject'])


def downgrade() -> None:
    op.drop_constraint('uq_user_oauth_subject', 'user', type_='unique')
    op.drop_column('user', 'oauth_subject')
    op.drop_column('user', 'oauth_provider')
    op.drop_column('user', 'auth_provider')
