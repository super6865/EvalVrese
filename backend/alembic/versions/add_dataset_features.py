"""Add dataset features from coze-loop

Revision ID: add_dataset_features
Revises: 2632284f2851
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'add_dataset_features'
down_revision: Union[str, None] = '2632284f2851'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def index_exists(table_name: str, index_name: str) -> bool:
    """Check if an index exists"""
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
    return index_name in indexes


def upgrade() -> None:
    # Add new fields to datasets table (only if they don't exist)
    if not column_exists('datasets', 'status'):
        op.add_column('datasets', sa.Column('status', sa.String(length=20), server_default=sa.text("'Available'"), nullable=True))
    if not column_exists('datasets', 'item_count'):
        op.add_column('datasets', sa.Column('item_count', sa.BigInteger(), server_default=sa.text('0'), nullable=True))
    if not column_exists('datasets', 'change_uncommitted'):
        op.add_column('datasets', sa.Column('change_uncommitted', sa.Boolean(), server_default=sa.text('0'), nullable=True))
    if not column_exists('datasets', 'latest_version'):
        op.add_column('datasets', sa.Column('latest_version', sa.String(length=50), nullable=True))
    if not column_exists('datasets', 'next_version_num'):
        op.add_column('datasets', sa.Column('next_version_num', sa.BigInteger(), server_default=sa.text('1'), nullable=True))
    if not column_exists('datasets', 'biz_category'):
        op.add_column('datasets', sa.Column('biz_category', sa.String(length=100), nullable=True))
    if not column_exists('datasets', 'spec'):
        op.add_column('datasets', sa.Column('spec', sa.JSON(), nullable=True))
    if not column_exists('datasets', 'features'):
        op.add_column('datasets', sa.Column('features', sa.JSON(), nullable=True))
    
    # Create index only if it doesn't exist
    if not index_exists('datasets', 'ix_datasets_status'):
        op.create_index(op.f('ix_datasets_status'), 'datasets', ['status'], unique=False)
    
    # Add new fields to dataset_versions table
    # Check if schema_id is already nullable
    bind = op.get_bind()
    inspector = inspect(bind)
    schema_id_col = next((col for col in inspector.get_columns('dataset_versions') if col['name'] == 'schema_id'), None)
    if schema_id_col and schema_id_col['nullable'] is False:
        # MySQL requires full column type when altering
        op.alter_column('dataset_versions', 'schema_id',
                       existing_type=sa.Integer(),
                       nullable=True)
    
    if not column_exists('dataset_versions', 'version_num'):
        op.add_column('dataset_versions', sa.Column('version_num', sa.BigInteger(), nullable=True))
    if not column_exists('dataset_versions', 'item_count'):
        op.add_column('dataset_versions', sa.Column('item_count', sa.BigInteger(), server_default=sa.text('0'), nullable=True))
    if not column_exists('dataset_versions', 'evaluation_set_schema'):
        op.add_column('dataset_versions', sa.Column('evaluation_set_schema', sa.JSON(), nullable=True))
    
    if not index_exists('dataset_versions', 'ix_dataset_versions_version'):
        op.create_index(op.f('ix_dataset_versions_version'), 'dataset_versions', ['version'], unique=False)
    
    # Add schema_id to dataset_items table
    if not column_exists('dataset_items', 'schema_id'):
        op.add_column('dataset_items', sa.Column('schema_id', sa.Integer(), nullable=True))
        op.create_foreign_key('fk_dataset_items_schema', 'dataset_items', 'dataset_schemas', ['schema_id'], ['id'])
    
    # Make version_id nullable for draft items
    version_id_col = next((col for col in inspector.get_columns('dataset_items') if col['name'] == 'version_id'), None)
    if version_id_col and version_id_col['nullable'] is False:
        # MySQL requires full column type when altering
        op.alter_column('dataset_items', 'version_id',
                       existing_type=sa.Integer(),
                       nullable=True)


def downgrade() -> None:
    # Remove indexes
    if index_exists('dataset_versions', 'ix_dataset_versions_version'):
        op.drop_index(op.f('ix_dataset_versions_version'), table_name='dataset_versions')
    if index_exists('datasets', 'ix_datasets_status'):
        op.drop_index(op.f('ix_datasets_status'), table_name='datasets')
    
    # Revert dataset_items changes
    if column_exists('dataset_items', 'version_id'):
        op.alter_column('dataset_items', 'version_id',
                       existing_type=sa.Integer(),
                       nullable=False)
    if column_exists('dataset_items', 'schema_id'):
        op.drop_constraint('fk_dataset_items_schema', 'dataset_items', type_='foreignkey')
        op.drop_column('dataset_items', 'schema_id')
    
    # Revert dataset_versions changes
    if column_exists('dataset_versions', 'evaluation_set_schema'):
        op.drop_column('dataset_versions', 'evaluation_set_schema')
    if column_exists('dataset_versions', 'item_count'):
        op.drop_column('dataset_versions', 'item_count')
    if column_exists('dataset_versions', 'version_num'):
        op.drop_column('dataset_versions', 'version_num')
    if column_exists('dataset_versions', 'schema_id'):
        op.alter_column('dataset_versions', 'schema_id',
                       existing_type=sa.Integer(),
                       nullable=False)
    
    # Revert datasets changes
    if column_exists('datasets', 'features'):
        op.drop_column('datasets', 'features')
    if column_exists('datasets', 'spec'):
        op.drop_column('datasets', 'spec')
    if column_exists('datasets', 'biz_category'):
        op.drop_column('datasets', 'biz_category')
    if column_exists('datasets', 'next_version_num'):
        op.drop_column('datasets', 'next_version_num')
    if column_exists('datasets', 'latest_version'):
        op.drop_column('datasets', 'latest_version')
    if column_exists('datasets', 'change_uncommitted'):
        op.drop_column('datasets', 'change_uncommitted')
    if column_exists('datasets', 'item_count'):
        op.drop_column('datasets', 'item_count')
    if column_exists('datasets', 'status'):
        op.drop_column('datasets', 'status')

