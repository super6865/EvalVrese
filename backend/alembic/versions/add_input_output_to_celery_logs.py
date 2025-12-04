"""add input_output to celery_task_logs

Revision ID: add_input_output_to_celery_logs
Revises: 2e50a4419854
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'add_input_output_to_celery_logs'
down_revision: Union[str, None] = '2e50a4419854'  # This should be the merge migration
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Add input_data and output_data columns to celery_task_logs table
    if not column_exists('celery_task_logs', 'input_data'):
        op.add_column('celery_task_logs', sa.Column('input_data', sa.JSON(), nullable=True))
    
    if not column_exists('celery_task_logs', 'output_data'):
        op.add_column('celery_task_logs', sa.Column('output_data', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove input_data and output_data columns
    if column_exists('celery_task_logs', 'input_data'):
        op.drop_column('celery_task_logs', 'input_data')
    
    if column_exists('celery_task_logs', 'output_data'):
        op.drop_column('celery_task_logs', 'output_data')

