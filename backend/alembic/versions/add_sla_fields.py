"""add_sla_fields

Revision ID: add_sla_fields_2026
Revises: a8c3f1d5e2b9
Create Date: 2026-04-28 10:00:00.000000

Add SLA fields to workflow_template_node and workflow_node tables:
  - workflow_template_node.sla_hours: Integer, nullable, SLA timeout in hours
  - workflow_node.sla_status: String(20), nullable, values: on_track, at_risk, overdue
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_sla_fields_2026'
down_revision: Union[str, None] = 'a8c3f1d5e2b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add sla_hours column to workflow_template_node
    op.add_column(
        'workflow_template_node',
        sa.Column('sla_hours', sa.Integer(), nullable=True)
    )

    # Add sla_status column to workflow_node
    # (planned_finish_time already exists from initial migration)
    op.add_column(
        'workflow_node',
        sa.Column('sla_status', sa.String(length=20), nullable=True)
    )


def downgrade() -> None:
    # Remove sla_status from workflow_node
    op.drop_column('workflow_node', 'sla_status')

    # Remove sla_hours from workflow_template_node
    op.drop_column('workflow_template_node', 'sla_hours')
