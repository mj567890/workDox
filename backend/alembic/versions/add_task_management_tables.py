"""add_task_management_tables

Revision ID: add_task_mgmt_2026
Revises: add_auth_provider_2026
Create Date: 2026-04-30 16:00:00.000000

Add 7 tables for the document task engine:
  task_template, stage_template, slot_template (definition layer)
  task_instance, task_stage, task_slot, slot_version (instance layer)
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


revision: str = 'add_task_mgmt_2026'
down_revision: Union[str, None] = 'add_auth_provider_2026'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('task_template',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('is_system', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table('stage_template',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('deadline_offset_days', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['template_id'], ['task_template.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table('slot_template',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('stage_template_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_required', sa.Boolean(), server_default=sa.text('true')),
        sa.Column('file_type_hints', JSON, nullable=True),
        sa.Column('auto_tags', JSON, nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['stage_template_id'], ['stage_template.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table('task_instance',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('matter_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('current_stage_order', sa.Integer(), server_default=sa.text('1')),
        sa.Column('creator_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['template_id'], ['task_template.id']),
        sa.ForeignKeyConstraint(['matter_id'], ['matter.id']),
        sa.ForeignKeyConstraint(['creator_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table('task_stage',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('stage_template_id', sa.Integer(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('status', sa.String(20), server_default='locked'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['task_id'], ['task_instance.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['stage_template_id'], ['stage_template.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table('task_slot',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('stage_id', sa.Integer(), nullable=False),
        sa.Column('slot_template_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_required', sa.Boolean(), server_default=sa.text('true')),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('waive_reason', sa.Text(), nullable=True),
        sa.Column('maturity', sa.String(20), nullable=True),
        sa.Column('maturity_note', sa.Text(), nullable=True),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['stage_id'], ['task_stage.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['slot_template_id'], ['slot_template.id']),
        sa.ForeignKeyConstraint(['document_id'], ['document.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table('slot_version',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slot_id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('maturity', sa.String(20), nullable=True),
        sa.Column('maturity_note', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['slot_id'], ['task_slot.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['document.id']),
        sa.ForeignKeyConstraint(['created_by'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('slot_version')
    op.drop_table('task_slot')
    op.drop_table('task_stage')
    op.drop_table('task_instance')
    op.drop_table('slot_template')
    op.drop_table('stage_template')
    op.drop_table('task_template')
