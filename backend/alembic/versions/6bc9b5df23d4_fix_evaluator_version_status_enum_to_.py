"""fix_evaluator_version_status_enum_to_lowercase

Revision ID: 6bc9b5df23d4
Revises: 071b7f2f8ba7
Create Date: 2025-11-27 15:14:09.311037

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6bc9b5df23d4'
down_revision: Union[str, None] = '071b7f2f8ba7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Fix evaluator_versions.status enum to use lowercase values (matching Python enum)
    bind = op.get_bind()
    if bind.dialect.name == 'mysql':
        # First, update existing data from uppercase to lowercase
        op.execute(sa.text("""
            UPDATE evaluator_versions 
            SET status = LOWER(status)
            WHERE status IN ('DRAFT', 'SUBMITTED', 'ARCHIVED')
        """))
        
        # Then, update the enum definition to use lowercase
        op.execute(sa.text("""
            ALTER TABLE evaluator_versions 
            MODIFY COLUMN status ENUM('draft', 'submitted', 'archived') NOT NULL DEFAULT 'draft'
        """))


def downgrade() -> None:
    # Revert evaluator_versions.status enum back to uppercase
    bind = op.get_bind()
    if bind.dialect.name == 'mysql':
        # First, update existing data from lowercase to uppercase
        op.execute(sa.text("""
            UPDATE evaluator_versions 
            SET status = UPPER(status)
            WHERE status IN ('draft', 'submitted', 'archived')
        """))
        
        # Then, update the enum definition to use uppercase
        op.execute(sa.text("""
            ALTER TABLE evaluator_versions 
            MODIFY COLUMN status ENUM('DRAFT', 'SUBMITTED', 'ARCHIVED') NOT NULL DEFAULT 'DRAFT'
        """))

