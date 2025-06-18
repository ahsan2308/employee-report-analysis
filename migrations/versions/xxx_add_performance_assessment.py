"""Add performance assessment fields

Revision ID: 812ef54a9d2b
Revises: 1cee61420935
Create Date: 2025-06-10 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = '812ef54a9d2b'
down_revision: Union[str, None] = '1cee61420935'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new columns to employee_analyses table for performance assessment
    op.add_column(
        'employee_analyses',
        sa.Column('performance_rating', sa.String(), nullable=True),
        schema='employee_reports'
    )
    op.add_column(
        'employee_analyses',
        sa.Column('performance_summary', sa.Text(), nullable=True),
        schema='employee_reports'
    )
    op.add_column(
        'employee_analyses',
        sa.Column('performance_strengths', JSONB(), nullable=True),
        schema='employee_reports'
    )
    op.add_column(
        'employee_analyses',
        sa.Column('performance_improvement_areas', JSONB(), nullable=True),
        schema='employee_reports'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('employee_analyses', 'performance_rating', schema='employee_reports')
    op.drop_column('employee_analyses', 'performance_summary', schema='employee_reports')
    op.drop_column('employee_analyses', 'performance_strengths', schema='employee_reports')
    op.drop_column('employee_analyses', 'performance_improvement_areas', schema='employee_reports')
