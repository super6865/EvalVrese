"""add_experiment_groups

Revision ID: 114e63fc9c8b
Revises: 62a7722417fd
Create Date: 2025-12-29 19:25:40.334663

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '114e63fc9c8b'
down_revision: Union[str, None] = '62a7722417fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create experiment_groups table
    op.create_table('experiment_groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['experiment_groups.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_experiment_groups_id'), 'experiment_groups', ['id'], unique=False)
    op.create_index(op.f('ix_experiment_groups_name'), 'experiment_groups', ['name'], unique=False)
    op.create_index(op.f('ix_experiment_groups_parent_id'), 'experiment_groups', ['parent_id'], unique=False)
    
    # Add group_id column to experiments table
    op.add_column('experiments', sa.Column('group_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_experiments_group_id'), 'experiments', ['group_id'], unique=False)
    op.create_foreign_key('fk_experiments_group_id', 'experiments', 'experiment_groups', ['group_id'], ['id'])


def downgrade() -> None:
    # Remove group_id column from experiments table
    op.drop_constraint('fk_experiments_group_id', 'experiments', type_='foreignkey')
    op.drop_index(op.f('ix_experiments_group_id'), table_name='experiments')
    op.drop_column('experiments', 'group_id')
    
    # Drop experiment_groups table
    op.drop_index(op.f('ix_experiment_groups_parent_id'), table_name='experiment_groups')
    op.drop_index(op.f('ix_experiment_groups_name'), table_name='experiment_groups')
    op.drop_index(op.f('ix_experiment_groups_id'), table_name='experiment_groups')
    op.drop_table('experiment_groups')

