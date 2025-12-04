"""merge_dataset_io_jobs_and_celery_logs

Revision ID: 2e50a4419854
Revises: add_dataset_io_jobs, add_task_id_and_celery_logs
Create Date: 2025-12-02 16:55:21.014135

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e50a4419854'
down_revision: Union[str, None] = ('add_dataset_io_jobs', 'add_task_id_and_celery_logs')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

