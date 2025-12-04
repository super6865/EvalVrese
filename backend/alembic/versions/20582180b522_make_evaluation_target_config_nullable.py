"""make_evaluation_target_config_nullable

Revision ID: 20582180b522
Revises: 29a455994d5e
Create Date: 2025-11-27 10:58:28.361329

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '20582180b522'
down_revision: Union[str, None] = '29a455994d5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Make evaluation_target_config nullable
    if column_exists('experiments', 'evaluation_target_config'):
        op.alter_column('experiments', 'evaluation_target_config',
                       existing_type=sa.JSON(),
                       nullable=True)


def downgrade() -> None:
    # Revert evaluation_target_config to not nullable
    # Note: This may fail if there are NULL values
    if column_exists('experiments', 'evaluation_target_config'):
        op.alter_column('experiments', 'evaluation_target_config',
                       existing_type=sa.JSON(),
                       nullable=False)

