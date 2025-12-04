"""merge model_sets and celery_logs branches

Revision ID: 88b8a5ca9d20
Revises: add_input_output_to_celery_logs, 4d20649513b7
Create Date: 2025-12-02 20:15:13.208466

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '88b8a5ca9d20'
down_revision: Union[str, None] = ('add_input_output_to_celery_logs', '4d20649513b7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

