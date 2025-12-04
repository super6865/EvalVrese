"""add model_configs table

Revision ID: 5e7ebdeaea79
Revises: 6bc9b5df23d4
Create Date: 2025-01-27 16:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5e7ebdeaea79'
down_revision: Union[str, None] = '6bc9b5df23d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'model_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('config_name', sa.String(length=255), nullable=False),
        sa.Column('model_type', sa.String(length=50), nullable=False),
        sa.Column('model_version', sa.String(length=100), nullable=False),
        sa.Column('api_key', sa.Text(), nullable=False),
        sa.Column('api_base', sa.String(length=500), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('max_tokens', sa.Integer(), nullable=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_model_configs_id'), 'model_configs', ['id'], unique=False)
    op.create_index(op.f('ix_model_configs_config_name'), 'model_configs', ['config_name'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_model_configs_config_name'), table_name='model_configs')
    op.drop_index(op.f('ix_model_configs_id'), table_name='model_configs')
    op.drop_table('model_configs')

