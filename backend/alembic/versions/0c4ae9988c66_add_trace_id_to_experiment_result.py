"""add trace_id to experiment_result

Revision ID: 0c4ae9988c66
Revises: 643bb7505d52
Create Date: 2025-01-27 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '0c4ae9988c66'
down_revision = '643bb7505d52'  # Latest migration
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def index_exists(table_name: str, index_name: str) -> bool:
    """Check if an index exists"""
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
    return index_name in indexes


def upgrade() -> None:
    # Add trace_id column to experiment_results table (if it doesn't exist)
    if not column_exists('experiment_results', 'trace_id'):
        op.add_column('experiment_results', sa.Column('trace_id', sa.String(64), nullable=True))
    
    # Add index on trace_id for faster lookups (if it doesn't exist)
    if not index_exists('experiment_results', 'idx_experiment_result_trace_id'):
        op.create_index('idx_experiment_result_trace_id', 'experiment_results', ['trace_id'])


def downgrade() -> None:
    # Remove index (if it exists)
    if index_exists('experiment_results', 'idx_experiment_result_trace_id'):
        op.drop_index('idx_experiment_result_trace_id', table_name='experiment_results')
    
    # Remove column (if it exists)
    if column_exists('experiment_results', 'trace_id'):
        op.drop_column('experiment_results', 'trace_id')
