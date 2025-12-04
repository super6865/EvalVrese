"""Add unique constraint to datasets.name

Revision ID: add_dataset_name_unique
Revises: add_dataset_features
Create Date: 2025-11-26 16:35:07.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = 'add_dataset_name_unique'
down_revision: Union[str, None] = 'add_dataset_features'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def constraint_exists(table_name: str, constraint_name: str) -> bool:
    """Check if a constraint exists"""
    bind = op.get_bind()
    inspector = inspect(bind)
    constraints = [c['name'] for c in inspector.get_unique_constraints(table_name)]
    return constraint_name in constraints


def upgrade() -> None:
    # Handle duplicate names before adding unique constraint
    bind = op.get_bind()
    
    # Find duplicate names
    result = bind.execute(text("""
        SELECT name, COUNT(*) as cnt, GROUP_CONCAT(id ORDER BY id) as ids
        FROM datasets
        GROUP BY name
        HAVING cnt > 1
    """))
    
    duplicates = result.fetchall()
    
    # Rename duplicate datasets (keep the first one, rename others)
    for row in duplicates:
        name = row[0]
        ids = [int(id_str) for id_str in row[2].split(',')]
        
        # Keep the first dataset with this name, rename others
        for idx, dataset_id in enumerate(ids[1:], start=1):
            new_name = f"{name}_{dataset_id}"
            # Ensure the new name doesn't conflict with existing names
            counter = 1
            while True:
                check_result = bind.execute(
                    text("SELECT COUNT(*) FROM datasets WHERE name = :new_name"),
                    {"new_name": new_name}
                )
                if check_result.scalar() == 0:
                    break
                new_name = f"{name}_{dataset_id}_{counter}"
                counter += 1
            
            bind.execute(
                text("UPDATE datasets SET name = :new_name WHERE id = :id"),
                {"new_name": new_name, "id": dataset_id}
            )
    
    # Add unique constraint to datasets.name
    if not constraint_exists('datasets', 'uq_datasets_name'):
        op.create_unique_constraint('uq_datasets_name', 'datasets', ['name'])


def downgrade() -> None:
    # Remove unique constraint from datasets.name
    if constraint_exists('datasets', 'uq_datasets_name'):
        op.drop_constraint('uq_datasets_name', 'datasets', type_='unique')

