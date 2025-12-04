"""fix_content_field_nullable

Revision ID: 7c043df686aa
Revises: add_evaluator_features
Create Date: 2025-11-26 23:42:08.698593

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c043df686aa'
down_revision: Union[str, None] = 'add_evaluator_features'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Change content field from NOT NULL to nullable=True
    # This matches the model definition in evaluator.py
    op.alter_column('evaluator_versions', 'content',
                   existing_type=sa.JSON(),
                   nullable=True)


def downgrade() -> None:
    # Revert content field back to NOT NULL
    # Note: This may fail if there are NULL values in the column
    op.alter_column('evaluator_versions', 'content',
                   existing_type=sa.JSON(),
                   nullable=False)

