"""add model_sets table

Revision ID: 4d20649513b7
Revises: 28c5af350d16
Create Date: 2025-12-02 20:03:50.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4d20649513b7'
down_revision: Union[str, None] = '28c5af350d16'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'model_sets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_model_sets_id'), 'model_sets', ['id'], unique=False)
    op.create_index(op.f('ix_model_sets_name'), 'model_sets', ['name'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_model_sets_name'), table_name='model_sets')
    op.drop_index(op.f('ix_model_sets_id'), table_name='model_sets')
    op.drop_table('model_sets')

