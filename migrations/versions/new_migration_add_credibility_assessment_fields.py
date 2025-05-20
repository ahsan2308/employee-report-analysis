"""Add credibility assessment fields

Revision ID: create_a_unique_id_here
Revises: 320fec19a06a
Create Date: 2025-05-05 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = 'create_a_unique_id_here'  # Replace with actual generated ID
down_revision: Union[str, None] = '320fec19a06a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new columns to employee_analyses table
    op.add_column(
        'employee_analyses',
        sa.Column('credibility_rating', sa.String(), nullable=True),
        schema='employee_reports'
    )
    op.add_column(
        'employee_analyses',
        sa.Column('credibility_explanation', sa.String(), nullable=True),
        schema='employee_reports'
    )
    op.add_column(
        'employee_analyses',
        sa.Column('consistency_score', sa.String(), nullable=True),
        schema='employee_reports'
    )
    op.add_column(
        'employee_analyses',
        sa.Column('exaggeration_flags', JSONB(), nullable=True),
        schema='employee_reports'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('employee_analyses', 'credibility_rating', schema='employee_reports')
    op.drop_column('employee_analyses', 'credibility_explanation', schema='employee_reports')
    op.drop_column('employee_analyses', 'consistency_score', schema='employee_reports')
    op.drop_column('employee_analyses', 'exaggeration_flags', schema='employee_reports')
