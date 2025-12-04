"""add_experiment_features

Revision ID: 29a455994d5e
Revises: 7c043df686aa
Create Date: 2025-11-27 09:56:18.570494

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '29a455994d5e'
down_revision: Union[str, None] = '7c043df686aa'
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
    # Add new columns to experiments table
    if not column_exists('experiments', 'item_concur_num'):
        op.add_column('experiments', sa.Column('item_concur_num', sa.Integer(), server_default='1', nullable=False))
    if not column_exists('experiments', 'expt_type'):
        op.add_column('experiments', sa.Column('expt_type', sa.Enum('OFFLINE', 'ONLINE', name='experimenttype'), server_default='OFFLINE', nullable=False))
    if not column_exists('experiments', 'max_alive_time'):
        op.add_column('experiments', sa.Column('max_alive_time', sa.Integer(), nullable=True))
    
    # Update experiment status enum to include new statuses
    bind = op.get_bind()
    if bind.dialect.name == 'mysql':
        # Check current enum values
        result = bind.execute(sa.text("""
            SELECT COLUMN_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'experiments' 
            AND COLUMN_NAME = 'status'
        """))
        current_type = result.scalar()
        if current_type and 'TERMINATED' not in current_type:
            # Update enum to include new statuses
            op.execute(sa.text("""
                ALTER TABLE experiments 
                MODIFY COLUMN status ENUM('pending', 'running', 'completed', 'failed', 'stopped', 'terminated', 'terminating') NOT NULL DEFAULT 'pending'
            """))
    
    # Create experiment_aggregate_results table
    if not table_exists('experiment_aggregate_results'):
        op.create_table(
            'experiment_aggregate_results',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('experiment_id', sa.Integer(), nullable=False),
            sa.Column('evaluator_version_id', sa.Integer(), nullable=False),
            sa.Column('aggregate_data', sa.JSON(), nullable=False),
            sa.Column('average_score', sa.Float(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['experiment_id'], ['experiments.id'], ),
            sa.ForeignKeyConstraint(['evaluator_version_id'], ['evaluator_versions.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_experiment_aggregate_results_id'), 'experiment_aggregate_results', ['id'], unique=False)
        op.create_index(op.f('ix_experiment_aggregate_results_experiment_id'), 'experiment_aggregate_results', ['experiment_id'], unique=False)
        op.create_index(op.f('ix_experiment_aggregate_results_evaluator_version_id'), 'experiment_aggregate_results', ['evaluator_version_id'], unique=False)
    
    # Create experiment_result_exports table
    if not table_exists('experiment_result_exports'):
        op.create_table(
            'experiment_result_exports',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('experiment_id', sa.Integer(), nullable=False),
            sa.Column('status', sa.Enum('PENDING', 'RUNNING', 'SUCCESS', 'FAILED', name='exportstatus'), server_default='PENDING', nullable=False),
            sa.Column('file_url', sa.String(length=500), nullable=True),
            sa.Column('file_name', sa.String(length=255), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.Column('created_by', sa.String(length=100), nullable=True),
            sa.ForeignKeyConstraint(['experiment_id'], ['experiments.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_experiment_result_exports_id'), 'experiment_result_exports', ['id'], unique=False)
        op.create_index(op.f('ix_experiment_result_exports_experiment_id'), 'experiment_result_exports', ['experiment_id'], unique=False)


def downgrade() -> None:
    # Drop experiment_result_exports table
    if table_exists('experiment_result_exports'):
        op.drop_index(op.f('ix_experiment_result_exports_experiment_id'), table_name='experiment_result_exports')
        op.drop_index(op.f('ix_experiment_result_exports_id'), table_name='experiment_result_exports')
        op.drop_table('experiment_result_exports')
    
    # Drop experiment_aggregate_results table
    if table_exists('experiment_aggregate_results'):
        op.drop_index(op.f('ix_experiment_aggregate_results_evaluator_version_id'), table_name='experiment_aggregate_results')
        op.drop_index(op.f('ix_experiment_aggregate_results_experiment_id'), table_name='experiment_aggregate_results')
        op.drop_index(op.f('ix_experiment_aggregate_results_id'), table_name='experiment_aggregate_results')
        op.drop_table('experiment_aggregate_results')
    
    # Revert experiments table changes
    if column_exists('experiments', 'max_alive_time'):
        op.drop_column('experiments', 'max_alive_time')
    if column_exists('experiments', 'expt_type'):
        op.drop_column('experiments', 'expt_type')
    if column_exists('experiments', 'item_concur_num'):
        op.drop_column('experiments', 'item_concur_num')

