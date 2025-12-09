"""add prompt tables

Revision ID: a1b2c3d4e5f6
Revises: fdba009d42ca
Create Date: 2025-01-15 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create prompts table
    op.create_table(
        'prompts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('prompt_key', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('latest_version', sa.String(length=50), nullable=True),
        sa.Column('latest_committed_at', sa.DateTime(), nullable=True),
        sa.Column('draft_detail', sa.JSON(), nullable=True),
        sa.Column('draft_updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=20), server_default=sa.text("'active'"), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_prompts_id'), 'prompts', ['id'], unique=False)
    op.create_index(op.f('ix_prompts_prompt_key'), 'prompts', ['prompt_key'], unique=True)
    op.create_index(op.f('ix_prompts_status'), 'prompts', ['status'], unique=False)
    
    # Create prompt_versions table
    op.create_table(
        'prompt_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('prompt_id', sa.Integer(), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('content', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['prompt_id'], ['prompts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_prompt_versions_id'), 'prompt_versions', ['id'], unique=False)
    op.create_index(op.f('ix_prompt_versions_version'), 'prompt_versions', ['version'], unique=False)
    
    # Create prompt_executions table
    op.create_table(
        'prompt_executions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('prompt_id', sa.Integer(), nullable=False),
        sa.Column('input_data', sa.JSON(), nullable=True),
        sa.Column('output_content', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('success', sa.Boolean(), server_default=sa.text('1'), nullable=True),
        sa.Column('usage', sa.JSON(), nullable=True),
        sa.Column('time_consuming_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['prompt_id'], ['prompts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_prompt_executions_id'), 'prompt_executions', ['id'], unique=False)
    op.create_index(op.f('ix_prompt_executions_prompt_id'), 'prompt_executions', ['prompt_id'], unique=False)
    op.create_index(op.f('ix_prompt_executions_created_at'), 'prompt_executions', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_prompt_executions_created_at'), table_name='prompt_executions')
    op.drop_index(op.f('ix_prompt_executions_prompt_id'), table_name='prompt_executions')
    op.drop_index(op.f('ix_prompt_executions_id'), table_name='prompt_executions')
    op.drop_table('prompt_executions')
    
    op.drop_index(op.f('ix_prompt_versions_version'), table_name='prompt_versions')
    op.drop_index(op.f('ix_prompt_versions_id'), table_name='prompt_versions')
    op.drop_table('prompt_versions')
    
    op.drop_index(op.f('ix_prompts_status'), table_name='prompts')
    op.drop_index(op.f('ix_prompts_prompt_key'), table_name='prompts')
    op.drop_index(op.f('ix_prompts_id'), table_name='prompts')
    op.drop_table('prompts')

