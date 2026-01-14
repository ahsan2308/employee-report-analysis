"""sync type enum update

Revision ID: 3379963e0751
Revises: 407c40171b98
Create Date: 2026-01-13 16:54:25.822507

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3379963e0751'
down_revision: Union[str, None] = '407c40171b98'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the old constraint that only allowed 'employee_reports' and 'vision_data'
    op.drop_constraint('check_valid_sync_type', 'sync_history', schema='employee_reports')
    
    # Add the new constraint with all SyncType enum values
    op.create_check_constraint(
        'check_valid_sync_type',
        'sync_history',
        "sync_type IN ('employee_reports', 'vision_data', 'job_descriptions', 'supervisor_feedback')",
        schema='employee_reports'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the new constraint
    op.drop_constraint('check_valid_sync_type', 'sync_history', schema='employee_reports')
    
    # Restore the old constraint
    op.create_check_constraint(
        'check_valid_sync_type',
        'sync_history',
        "sync_type IN ('employee_reports', 'vision_data')",
        schema='employee_reports'
    )
