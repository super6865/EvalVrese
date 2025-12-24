"""remove_dataset_name_unique_constraint

Revision ID: 5d74a8571f93
Revises: a1b2c3d4e5f6
Create Date: 2025-12-24 15:18:31.155950

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '5d74a8571f93'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def constraint_exists(table_name: str, constraint_name: str) -> bool:
    """Check if a constraint exists"""
    bind = op.get_bind()
    inspector = inspect(bind)
    constraints = [c['name'] for c in inspector.get_unique_constraints(table_name)]
    return constraint_name in constraints


def upgrade() -> None:
    # Remove unique constraint from datasets.name
    # This allows creating datasets with same name as deleted datasets
    # Name uniqueness is now enforced at application level (excluding deleted datasets)
    if constraint_exists('datasets', 'uq_datasets_name'):
        op.drop_constraint('uq_datasets_name', 'datasets', type_='unique')
    
    # Also remove the unique constraint from the column definition if it exists
    # (Some databases may have it defined at column level)
    try:
        op.drop_index('uq_datasets_name', table_name='datasets')
    except Exception:
        # Index might not exist or might be named differently, ignore
        pass


def downgrade() -> None:
    # Re-add unique constraint if downgrading
    if not constraint_exists('datasets', 'uq_datasets_name'):
        op.create_unique_constraint('uq_datasets_name', 'datasets', ['name'])

