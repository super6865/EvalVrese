"""Add dataset_io_jobs table

Revision ID: add_dataset_io_jobs
Revises: add_dataset_features
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'add_dataset_io_jobs'
down_revision: Union[str, None] = 'add_dataset_features'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create dataset_io_jobs table
    op.create_table(
        'dataset_io_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('dataset_id', sa.Integer(), nullable=False),
        sa.Column('job_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='Pending', nullable=True),
        sa.Column('source_file', sa.JSON(), nullable=True),
        sa.Column('target_dataset_id', sa.Integer(), nullable=True),
        sa.Column('field_mappings', sa.JSON(), nullable=True),
        sa.Column('option', sa.JSON(), nullable=True),
        sa.Column('total', sa.BigInteger(), nullable=True),
        sa.Column('processed', sa.BigInteger(), server_default='0', nullable=True),
        sa.Column('added', sa.BigInteger(), server_default='0', nullable=True),
        sa.Column('progress', sa.JSON(), nullable=True),
        sa.Column('sub_progresses', sa.JSON(), nullable=True),
        sa.Column('errors', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ),
        sa.ForeignKeyConstraint(['target_dataset_id'], ['datasets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dataset_io_jobs_id'), 'dataset_io_jobs', ['id'], unique=False)
    op.create_index(op.f('ix_dataset_io_jobs_dataset_id'), 'dataset_io_jobs', ['dataset_id'], unique=False)
    op.create_index(op.f('ix_dataset_io_jobs_status'), 'dataset_io_jobs', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_dataset_io_jobs_status'), table_name='dataset_io_jobs')
    op.drop_index(op.f('ix_dataset_io_jobs_dataset_id'), table_name='dataset_io_jobs')
    op.drop_index(op.f('ix_dataset_io_jobs_id'), table_name='dataset_io_jobs')
    op.drop_table('dataset_io_jobs')

