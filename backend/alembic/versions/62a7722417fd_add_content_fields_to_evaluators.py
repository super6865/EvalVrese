"""add_content_fields_to_evaluators

Revision ID: 62a7722417fd
Revises: 541114905308
Create Date: 2025-12-29 09:27:31.513558

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '62a7722417fd'
down_revision: Union[str, None] = '541114905308'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Add content fields to evaluators table
    if not column_exists('evaluators', 'prompt_content'):
        op.add_column('evaluators', sa.Column('prompt_content', sa.JSON(), nullable=True))
    if not column_exists('evaluators', 'code_content'):
        op.add_column('evaluators', sa.Column('code_content', sa.JSON(), nullable=True))
    if not column_exists('evaluators', 'input_schemas'):
        op.add_column('evaluators', sa.Column('input_schemas', sa.JSON(), nullable=True))
    if not column_exists('evaluators', 'output_schemas'):
        op.add_column('evaluators', sa.Column('output_schemas', sa.JSON(), nullable=True))
    
    # Migrate existing data from current versions to evaluators
    # This will sync content from the latest version (submitted or latest) to the evaluator
    bind = op.get_bind()
    # First, try to sync from submitted versions
    op.execute(sa.text("""
        UPDATE evaluators e
        INNER JOIN (
            SELECT ev.evaluator_id, 
                   ev.prompt_content,
                   ev.code_content,
                   ev.input_schemas,
                   ev.output_schemas
            FROM evaluator_versions ev
            INNER JOIN (
                SELECT evaluator_id, MAX(id) as max_id
                FROM evaluator_versions
                WHERE status = 'submitted'
                GROUP BY evaluator_id
            ) latest ON ev.id = latest.max_id
        ) latest_version ON e.id = latest_version.evaluator_id
        SET e.prompt_content = latest_version.prompt_content,
            e.code_content = latest_version.code_content,
            e.input_schemas = latest_version.input_schemas,
            e.output_schemas = latest_version.output_schemas
        WHERE (e.prompt_content IS NULL AND e.code_content IS NULL)
    """))
    
    # Then, sync from any latest version for evaluators that still don't have content
    op.execute(sa.text("""
        UPDATE evaluators e
        INNER JOIN (
            SELECT ev.evaluator_id, 
                   ev.prompt_content,
                   ev.code_content,
                   ev.input_schemas,
                   ev.output_schemas
            FROM evaluator_versions ev
            INNER JOIN (
                SELECT evaluator_id, MAX(id) as max_id
                FROM evaluator_versions
                GROUP BY evaluator_id
            ) latest ON ev.id = latest.max_id
        ) latest_version ON e.id = latest_version.evaluator_id
        SET e.prompt_content = latest_version.prompt_content,
            e.code_content = latest_version.code_content,
            e.input_schemas = latest_version.input_schemas,
            e.output_schemas = latest_version.output_schemas
        WHERE (e.prompt_content IS NULL AND e.code_content IS NULL)
    """))


def downgrade() -> None:
    # Remove content fields from evaluators table
    if column_exists('evaluators', 'output_schemas'):
        op.drop_column('evaluators', 'output_schemas')
    if column_exists('evaluators', 'input_schemas'):
        op.drop_column('evaluators', 'input_schemas')
    if column_exists('evaluators', 'code_content'):
        op.drop_column('evaluators', 'code_content')
    if column_exists('evaluators', 'prompt_content'):
        op.drop_column('evaluators', 'prompt_content')

