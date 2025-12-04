"""Add evaluator features from coze-loop

Revision ID: add_evaluator_features
Revises: add_dataset_name_unique
Create Date: 2025-11-26 17:16:52.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = 'add_evaluator_features'
down_revision: Union[str, None] = 'add_dataset_name_unique'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def table_exists(table_name: str) -> bool:
    """Check if a table exists"""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # Update evaluators table
    if not column_exists('evaluators', 'builtin'):
        op.add_column('evaluators', sa.Column('builtin', sa.Boolean(), server_default=sa.text('0'), nullable=False))
    if not column_exists('evaluators', 'box_type'):
        op.add_column('evaluators', sa.Column('box_type', sa.Enum('WHITE', 'BLACK', name='evaluatorboxtype'), nullable=True))
    if not column_exists('evaluators', 'evaluator_info'):
        op.add_column('evaluators', sa.Column('evaluator_info', sa.JSON(), nullable=True))
    if not column_exists('evaluators', 'tags'):
        op.add_column('evaluators', sa.Column('tags', sa.JSON(), nullable=True))
    
    # Update evaluator_versions table
    if not column_exists('evaluator_versions', 'input_schemas'):
        op.add_column('evaluator_versions', sa.Column('input_schemas', sa.JSON(), nullable=True))
    if not column_exists('evaluator_versions', 'output_schemas'):
        op.add_column('evaluator_versions', sa.Column('output_schemas', sa.JSON(), nullable=True))
    if not column_exists('evaluator_versions', 'prompt_content'):
        op.add_column('evaluator_versions', sa.Column('prompt_content', sa.JSON(), nullable=True))
    if not column_exists('evaluator_versions', 'code_content'):
        op.add_column('evaluator_versions', sa.Column('code_content', sa.JSON(), nullable=True))
    
    # Update status column to use enum
    # First, check if status column exists and update it
    if column_exists('evaluator_versions', 'status'):
        # Change status to use enum
        op.alter_column('evaluator_versions', 'status',
                       existing_type=sa.String(20),
                       type_=sa.Enum('DRAFT', 'SUBMITTED', 'ARCHIVED', name='evaluatorversionstatus'),
                       existing_nullable=True,
                       nullable=False,
                       server_default='DRAFT')
    else:
        op.add_column('evaluator_versions', 
                     sa.Column('status', sa.Enum('DRAFT', 'SUBMITTED', 'ARCHIVED', name='evaluatorversionstatus'), 
                              server_default='DRAFT', nullable=False))
    
    # Update evaluator_type enum to include PROMPT
    # Note: This is complex in MySQL, we'll handle it carefully
    bind = op.get_bind()
    if bind.dialect.name == 'mysql':
        # Check current enum values
        result = bind.execute(sa.text("""
            SELECT COLUMN_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'evaluators' 
            AND COLUMN_NAME = 'evaluator_type'
        """))
        current_type = result.scalar()
        if current_type and 'PROMPT' not in current_type:
            # Step 1: Temporarily change to VARCHAR to allow any value
            op.execute(sa.text("""
                ALTER TABLE evaluators 
                MODIFY COLUMN evaluator_type VARCHAR(20) NOT NULL
            """))
            # Step 2: Update existing data: convert 'autogen' to 'PROMPT'
            op.execute(sa.text("""
                UPDATE evaluators 
                SET evaluator_type = 'PROMPT' 
                WHERE evaluator_type = 'autogen' OR evaluator_type = 'AUTOGEN'
            """))
            # Step 3: Change back to ENUM with new values
            op.execute(sa.text("""
                ALTER TABLE evaluators 
                MODIFY COLUMN evaluator_type ENUM('PROMPT', 'CODE', 'CUSTOM_RPC') NOT NULL
            """))
    
    # Create evaluator_records table
    if not table_exists('evaluator_records'):
        op.create_table(
            'evaluator_records',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('evaluator_version_id', sa.Integer(), nullable=False),
            sa.Column('experiment_id', sa.Integer(), nullable=True),
            sa.Column('experiment_run_id', sa.Integer(), nullable=True),
            sa.Column('dataset_item_id', sa.Integer(), nullable=True),
            sa.Column('turn_id', sa.Integer(), nullable=True),
            sa.Column('input_data', sa.JSON(), nullable=False),
            sa.Column('output_data', sa.JSON(), nullable=False),
            sa.Column('status', sa.Enum('UNKNOWN', 'SUCCESS', 'FAIL', name='evaluatorrunstatus'), 
                     server_default='UNKNOWN', nullable=False),
            sa.Column('trace_id', sa.String(length=255), nullable=True),
            sa.Column('log_id', sa.String(length=255), nullable=True),
            sa.Column('ext', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('created_by', sa.String(length=100), nullable=True),
            sa.ForeignKeyConstraint(['evaluator_version_id'], ['evaluator_versions.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_evaluator_records_id'), 'evaluator_records', ['id'], unique=False)
        op.create_index(op.f('ix_evaluator_records_evaluator_version_id'), 'evaluator_records', ['evaluator_version_id'], unique=False)
        op.create_index(op.f('ix_evaluator_records_experiment_id'), 'evaluator_records', ['experiment_id'], unique=False)
        op.create_index(op.f('ix_evaluator_records_experiment_run_id'), 'evaluator_records', ['experiment_run_id'], unique=False)
        op.create_index(op.f('ix_evaluator_records_dataset_item_id'), 'evaluator_records', ['dataset_item_id'], unique=False)
        op.create_index(op.f('ix_evaluator_records_turn_id'), 'evaluator_records', ['turn_id'], unique=False)
        op.create_index(op.f('ix_evaluator_records_trace_id'), 'evaluator_records', ['trace_id'], unique=False)
        op.create_index(op.f('ix_evaluator_records_created_at'), 'evaluator_records', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop evaluator_records table
    if table_exists('evaluator_records'):
        op.drop_index(op.f('ix_evaluator_records_created_at'), table_name='evaluator_records')
        op.drop_index(op.f('ix_evaluator_records_trace_id'), table_name='evaluator_records')
        op.drop_index(op.f('ix_evaluator_records_turn_id'), table_name='evaluator_records')
        op.drop_index(op.f('ix_evaluator_records_dataset_item_id'), table_name='evaluator_records')
        op.drop_index(op.f('ix_evaluator_records_experiment_run_id'), table_name='evaluator_records')
        op.drop_index(op.f('ix_evaluator_records_experiment_id'), table_name='evaluator_records')
        op.drop_index(op.f('ix_evaluator_records_evaluator_version_id'), table_name='evaluator_records')
        op.drop_index(op.f('ix_evaluator_records_id'), table_name='evaluator_records')
        op.drop_table('evaluator_records')
    
    # Revert evaluator_versions changes
    if column_exists('evaluator_versions', 'code_content'):
        op.drop_column('evaluator_versions', 'code_content')
    if column_exists('evaluator_versions', 'prompt_content'):
        op.drop_column('evaluator_versions', 'prompt_content')
    if column_exists('evaluator_versions', 'output_schemas'):
        op.drop_column('evaluator_versions', 'output_schemas')
    if column_exists('evaluator_versions', 'input_schemas'):
        op.drop_column('evaluator_versions', 'input_schemas')
    if column_exists('evaluator_versions', 'status'):
        op.alter_column('evaluator_versions', 'status',
                       existing_type=sa.Enum('DRAFT', 'SUBMITTED', 'ARCHIVED', name='evaluatorversionstatus'),
                       type_=sa.String(20),
                       existing_nullable=False,
                       nullable=True,
                       server_default='draft')
    
    # Revert evaluators changes
    if column_exists('evaluators', 'tags'):
        op.drop_column('evaluators', 'tags')
    if column_exists('evaluators', 'evaluator_info'):
        op.drop_column('evaluators', 'evaluator_info')
    if column_exists('evaluators', 'box_type'):
        op.drop_column('evaluators', 'box_type')
    if column_exists('evaluators', 'builtin'):
        op.drop_column('evaluators', 'builtin')

