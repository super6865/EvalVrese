"""add_timeout_to_model_configs

Revision ID: 28c5af350d16
Revises: 5e7ebdeaea79
Create Date: 2025-12-01 17:13:06.372166

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28c5af350d16'
down_revision: Union[str, None] = '5e7ebdeaea79'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add timeout column to model_configs table with default value of 60
    op.add_column('model_configs', sa.Column('timeout', sa.Integer(), nullable=False, server_default='60'))


def downgrade() -> None:
    # Remove timeout column from model_configs table
    op.drop_column('model_configs', 'timeout')

