"""fix_evaluator_type_enum_to_lowercase

Revision ID: 071b7f2f8ba7
Revises: 0c4ae9988c66
Create Date: 2025-11-27 15:08:09.058411

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '071b7f2f8ba7'
down_revision: Union[str, None] = '0c4ae9988c66'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Fix evaluators.evaluator_type enum to use lowercase values (matching Python enum)
    bind = op.get_bind()
    if bind.dialect.name == 'mysql':
        # First, update existing data from uppercase to lowercase
        op.execute(sa.text("""
            UPDATE evaluators 
            SET evaluator_type = LOWER(evaluator_type)
            WHERE evaluator_type IN ('PROMPT', 'CODE', 'CUSTOM_RPC')
        """))
        
        # Then, update the enum definition to use lowercase
        # Note: Only 'prompt' and 'code' are defined in Python EvaluatorType enum
        # If CUSTOM_RPC exists in data, we'll convert it to lowercase but it won't be in the enum
        op.execute(sa.text("""
            ALTER TABLE evaluators 
            MODIFY COLUMN evaluator_type ENUM('prompt', 'code', 'custom_rpc') NOT NULL
        """))


def downgrade() -> None:
    # Revert evaluators.evaluator_type enum back to uppercase
    bind = op.get_bind()
    if bind.dialect.name == 'mysql':
        # First, update existing data from lowercase to uppercase
        op.execute(sa.text("""
            UPDATE evaluators 
            SET evaluator_type = UPPER(evaluator_type)
            WHERE evaluator_type IN ('prompt', 'code', 'custom_rpc')
        """))
        
        # Then, update the enum definition to use uppercase
        op.execute(sa.text("""
            ALTER TABLE evaluators 
            MODIFY COLUMN evaluator_type ENUM('PROMPT', 'CODE', 'CUSTOM_RPC') NOT NULL
        """))

