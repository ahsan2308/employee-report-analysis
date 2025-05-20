"""add_credibility_assessment_fields

Revision ID: b4e7ae76295f
Revises: create_a_unique_id_here
Create Date: 2025-05-20 14:17:29.771321

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4e7ae76295f'
down_revision: Union[str, None] = 'create_a_unique_id_here'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
