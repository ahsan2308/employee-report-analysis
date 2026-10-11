"""add partial import status

Revision ID: a7c3e91d4b52
Revises: 3379963e0751
Create Date: 2026-10-11 15:00:00.000000

"""
import os
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a7c3e91d4b52'
down_revision: Union[str, None] = '3379963e0751'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Same default as migrations/env.py
SCHEMA = os.getenv("SCHEMA_NAME", "employee_reports")


def _replace_status_check(statuses) -> None:
    # Databases built by these migrations never had the check (create_all() adds it), hence IF EXISTS
    op.execute(f'ALTER TABLE "{SCHEMA}".csv_import_jobs DROP CONSTRAINT IF EXISTS check_valid_import_status')
    op.create_check_constraint(
        'check_valid_import_status',
        'csv_import_jobs',
        "status IN (" + ", ".join(f"'{status}'" for status in statuses) + ")",
        schema=SCHEMA
    )


def upgrade() -> None:
    """Upgrade schema: an import that saved some rows but not all ends as 'partial'."""
    _replace_status_check(['pending', 'running', 'completed', 'partial', 'failed'])


def downgrade() -> None:
    """Downgrade schema: partial imports become completed, as they were reported before."""
    op.execute(f"UPDATE \"{SCHEMA}\".csv_import_jobs SET status = 'completed' WHERE status = 'partial'")
    _replace_status_check(['pending', 'running', 'completed', 'failed'])
