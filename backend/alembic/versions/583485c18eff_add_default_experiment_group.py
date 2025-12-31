"""add_default_experiment_group

Revision ID: 583485c18eff
Revises: 114e63fc9c8b
Create Date: 2025-12-29 19:48:49.017755

"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '583485c18eff'
down_revision: Union[str, None] = '114e63fc9c8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create default experiment group "通用实验" and migrate existing experiments to it.
    """
    bind = op.get_bind()
    
    # Check if experiment_groups table exists
    result = bind.execute(text("""
        SELECT COUNT(*) as count 
        FROM information_schema.tables 
        WHERE table_schema = DATABASE() 
        AND table_name = 'experiment_groups'
    """))
    
    if result.scalar() > 0:
        # Check if default group already exists
        default_group_result = bind.execute(text("""
            SELECT id FROM experiment_groups 
            WHERE name = '通用实验' AND parent_id IS NULL
            LIMIT 1
        """))
        
        default_group_id = None
        row = default_group_result.fetchone()
        if row:
            default_group_id = row[0]
        else:
            # Create default group "通用实验"
            now = datetime.utcnow()
            bind.execute(
                text("""
                    INSERT INTO experiment_groups (name, parent_id, description, created_at, updated_at)
                    VALUES (:name, NULL, :description, :created_at, :updated_at)
                """),
                {
                    "name": "通用实验",
                    "description": "默认实验分组，用于存放未分组的实验",
                    "created_at": now,
                    "updated_at": now
                }
            )
            # Get the inserted ID
            default_group_result = bind.execute(text("""
                SELECT id FROM experiment_groups 
                WHERE name = '通用实验' AND parent_id IS NULL
                LIMIT 1
            """))
            default_group_id = default_group_result.fetchone()[0]
        
        # Update all experiments with NULL group_id to the default group
        if default_group_id:
            bind.execute(
                text("""
                    UPDATE experiments 
                    SET group_id = :group_id 
                    WHERE group_id IS NULL
                """),
                {"group_id": default_group_id}
            )
            print(f"Migrated existing experiments to default group (ID: {default_group_id})")


def downgrade() -> None:
    """
    Remove default group assignment from experiments.
    Note: This will set group_id to NULL for experiments in the default group.
    """
    bind = op.get_bind()
    
    # Find default group
    default_group_result = bind.execute(text("""
        SELECT id FROM experiment_groups 
        WHERE name = '通用实验' AND parent_id IS NULL
        LIMIT 1
    """))
    
    row = default_group_result.fetchone()
    if row:
        default_group_id = row[0]
        # Set group_id to NULL for experiments in default group
        bind.execute(
            text("""
                UPDATE experiments 
                SET group_id = NULL 
                WHERE group_id = :group_id
            """),
            {"group_id": default_group_id}
        )
        # Optionally delete the default group (commented out to preserve data)
        # bind.execute(
        #     text("DELETE FROM experiment_groups WHERE id = :id"),
        #     {"id": default_group_id}
        # )

