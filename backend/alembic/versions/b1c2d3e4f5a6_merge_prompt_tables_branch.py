"""merge prompt tables branch

Revision ID: b1c2d3e4f5a6
Revises: fdba009d42ca, 88b8a5ca9d20
Create Date: 2025-01-15 10:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = ('fdba009d42ca', '88b8a5ca9d20')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

