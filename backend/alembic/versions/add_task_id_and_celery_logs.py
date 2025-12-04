"""add task_id and celery_task_logs table

Revision ID: add_task_id_and_celery_logs
Revises: 28c5af350d16
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'add_task_id_and_celery_logs'
down_revision: Union[str, None] = '28c5af350d16'
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
    # Add task_id column to experiment_runs table (if it doesn't exist)
    if not column_exists('experiment_runs', 'task_id'):
        op.add_column('experiment_runs', sa.Column('task_id', sa.String(255), nullable=True))
        op.create_index('ix_experiment_runs_task_id', 'experiment_runs', ['task_id'], unique=False)
    
    # Create celery_task_logs table
    if not table_exists('celery_task_logs'):
        op.create_table(
            'celery_task_logs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('experiment_id', sa.Integer(), nullable=False),
            sa.Column('run_id', sa.Integer(), nullable=False),
            sa.Column('task_id', sa.String(255), nullable=False),
            sa.Column('log_level', sa.Enum('INFO', 'ERROR', 'WARNING', 'DEBUG', name='celerytaskloglevel'), nullable=False),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('step_name', sa.String(100), nullable=True),
            sa.Column('timestamp', sa.DateTime(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['experiment_id'], ['experiments.id'], ),
            sa.ForeignKeyConstraint(['run_id'], ['experiment_runs.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_celery_task_logs_id'), 'celery_task_logs', ['id'], unique=False)
        op.create_index(op.f('ix_celery_task_logs_experiment_id'), 'celery_task_logs', ['experiment_id'], unique=False)
        op.create_index(op.f('ix_celery_task_logs_run_id'), 'celery_task_logs', ['run_id'], unique=False)
        op.create_index(op.f('ix_celery_task_logs_task_id'), 'celery_task_logs', ['task_id'], unique=False)
        op.create_index(op.f('ix_celery_task_logs_timestamp'), 'celery_task_logs', ['timestamp'], unique=False)


def downgrade() -> None:
    # Drop celery_task_logs table
    if table_exists('celery_task_logs'):
        op.drop_index(op.f('ix_celery_task_logs_timestamp'), table_name='celery_task_logs')
        op.drop_index(op.f('ix_celery_task_logs_task_id'), table_name='celery_task_logs')
        op.drop_index(op.f('ix_celery_task_logs_run_id'), table_name='celery_task_logs')
        op.drop_index(op.f('ix_celery_task_logs_experiment_id'), table_name='celery_task_logs')
        op.drop_index(op.f('ix_celery_task_logs_id'), table_name='celery_task_logs')
        op.drop_table('celery_task_logs')
    
    # Remove task_id column from experiment_runs table
    if column_exists('experiment_runs', 'task_id'):
        op.drop_index('ix_experiment_runs_task_id', table_name='experiment_runs')
        op.drop_column('experiment_runs', 'task_id')

