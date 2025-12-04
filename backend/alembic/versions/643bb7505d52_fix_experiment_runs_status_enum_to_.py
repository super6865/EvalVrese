"""fix_experiment_runs_status_enum_to_lowercase

Revision ID: 643bb7505d52
Revises: 20582180b522
Create Date: 2025-11-27 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '643bb7505d52'
down_revision: Union[str, None] = '20582180b522'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Fix experiment_runs.status enum to use lowercase values (matching experiments table)
    bind = op.get_bind()
    if bind.dialect.name == 'mysql':
        # First, update existing data from uppercase to lowercase
        op.execute(sa.text("""
            UPDATE experiment_runs 
            SET status = LOWER(status)
            WHERE status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'STOPPED')
        """))
        
        # Then, update the enum definition to use lowercase
        op.execute(sa.text("""
            ALTER TABLE experiment_runs 
            MODIFY COLUMN status ENUM('pending', 'running', 'completed', 'failed', 'stopped', 'terminated', 'terminating') NULL DEFAULT NULL
        """))


def downgrade() -> None:
    # Revert experiment_runs.status enum back to uppercase
    bind = op.get_bind()
    if bind.dialect.name == 'mysql':
        # First, update existing data from lowercase to uppercase
        op.execute(sa.text("""
            UPDATE experiment_runs 
            SET status = UPPER(status)
            WHERE status IN ('pending', 'running', 'completed', 'failed', 'stopped', 'terminated', 'terminating')
        """))
        
        # Then, update the enum definition to use uppercase
        op.execute(sa.text("""
            ALTER TABLE experiment_runs 
            MODIFY COLUMN status ENUM('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'STOPPED') NULL DEFAULT NULL
        """))
