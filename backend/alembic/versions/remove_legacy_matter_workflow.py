"""remove_legacy_matter_workflow

Revision ID: remove_legacy_2026
Revises: add_task_mgmt_2026
Create Date: 2026-04-30 18:00:00.000000

Remove legacy Matter, Workflow, and simple Task tables.
Drop FK columns: document.matter_id, notification.related_matter_id, task_instance.matter_id.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'remove_legacy_2026'
down_revision: Union[str, None] = 'add_task_mgmt_2026'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop FK constraints on columns we keep but detach from matter
    # task_instance.matter_id → kept column, drop FK then column
    op.drop_constraint('task_instance_matter_id_fkey', 'task_instance', type_='foreignkey')
    op.drop_column('task_instance', 'matter_id')

    # notification.related_matter_id → kept column, drop FK then column
    op.drop_constraint('notification_related_matter_id_fkey', 'notification', type_='foreignkey')
    op.drop_column('notification', 'related_matter_id')

    # document.matter_id → kept column, drop FK then column
    op.drop_constraint('document_matter_id_fkey', 'document', type_='foreignkey')
    op.drop_column('document', 'matter_id')

    # 2. Drop tables that depend on matter (in dependency order)
    # Drop FK from legacy task table to workflow_node first
    op.drop_constraint('task_node_id_fkey', 'task', type_='foreignkey')
    op.drop_table('workflow_node')
    op.drop_table('cross_matter_reference')
    op.drop_table('matter_comment')
    op.drop_table('matter_member')

    # 3. Drop workflow templates
    op.drop_table('workflow_template_node')
    op.drop_table('workflow_template')

    # 4. Drop legacy task table
    op.drop_table('task')

    # 5. Drop matter and matter_type
    op.drop_table('matter')
    op.drop_table('matter_type')


def downgrade() -> None:
    # Re-create matter_type
    op.create_table('matter_type',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )

    # Re-create matter
    op.create_table('matter',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('matter_no', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('type_id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('is_key_project', sa.Boolean(), nullable=False),
        sa.Column('progress', sa.Float(), nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['user.id']),
        sa.ForeignKeyConstraint(['type_id'], ['matter_type.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_matter_due', 'matter', ['due_date', 'status'], unique=False)
    op.create_index(op.f('ix_matter_matter_no'), 'matter', ['matter_no'], unique=True)
    op.create_index(op.f('ix_matter_status'), 'matter', ['status'], unique=False)

    # Re-create document.matter_id column + FK
    op.add_column('document', sa.Column('matter_id', sa.Integer(), nullable=True))
    op.create_foreign_key('document_matter_id_fkey', 'document', 'matter', ['matter_id'], ['id'])

    # Re-create notification.related_matter_id column + FK
    op.add_column('notification', sa.Column('related_matter_id', sa.Integer(), nullable=True))
    op.create_foreign_key('notification_related_matter_id_fkey', 'notification', 'matter', ['related_matter_id'], ['id'])

    # Re-create task_instance.matter_id column + FK
    op.add_column('task_instance', sa.Column('matter_id', sa.Integer(), nullable=True))
    op.create_foreign_key('task_instance_matter_id_fkey', 'task_instance', 'matter', ['matter_id'], ['id'])

    # Re-create dependent tables
    op.create_table('workflow_template',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('matter_type_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['matter_type_id'], ['matter_type.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('workflow_template_node',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('node_name', sa.String(length=200), nullable=False),
        sa.Column('node_order', sa.Integer(), nullable=False),
        sa.Column('owner_role', sa.String(length=50), nullable=False),
        sa.Column('required_documents_rule', sa.JSON(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['template_id'], ['workflow_template.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('template_id', 'node_order', name='uq_template_node_order'),
    )

    op.create_table('task',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('matter_id', sa.Integer(), nullable=False),
        sa.Column('node_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('assigner_id', sa.Integer(), nullable=False),
        sa.Column('assignee_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False),
        sa.Column('due_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['assignee_id'], ['user.id']),
        sa.ForeignKeyConstraint(['assigner_id'], ['user.id']),
        sa.ForeignKeyConstraint(['matter_id'], ['matter.id']),
        sa.ForeignKeyConstraint(['node_id'], ['workflow_node.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('matter_member',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('matter_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role_in_matter', sa.String(length=30), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['matter_id'], ['matter.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('matter_id', 'user_id', name='uq_matter_member'),
    )

    op.create_table('matter_comment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('matter_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['matter_id'], ['matter.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table('cross_matter_reference',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('matter_id', sa.Integer(), nullable=False),
        sa.Column('is_readonly', sa.Boolean(), nullable=False),
        sa.Column('added_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['added_by'], ['user.id']),
        sa.ForeignKeyConstraint(['document_id'], ['document.id']),
        sa.ForeignKeyConstraint(['matter_id'], ['matter.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id', 'matter_id', name='uq_doc_matter_ref'),
    )

    op.create_table('workflow_node',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('matter_id', sa.Integer(), nullable=False),
        sa.Column('node_name', sa.String(length=200), nullable=False),
        sa.Column('node_order', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('planned_finish_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_finish_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('required_documents_rule', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['matter_id'], ['matter.id']),
        sa.ForeignKeyConstraint(['owner_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('matter_id', 'node_order', name='uq_matter_node_order'),
    )
