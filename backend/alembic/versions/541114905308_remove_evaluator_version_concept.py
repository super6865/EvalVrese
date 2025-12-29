"""remove_evaluator_version_concept

Revision ID: 541114905308
Revises: 5d74a8571f93
Create Date: 2025-12-28 23:17:43.065537

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '541114905308'
down_revision: Union[str, None] = '5d74a8571f93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

