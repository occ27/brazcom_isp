"""merge heads

Revision ID: da0e3d37c8e8
Revises: 4ad0fb48ebe3, c3d9f2a4e6b7
Create Date: 2025-10-24 13:49:34.306118

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da0e3d37c8e8'
down_revision: Union[str, Sequence[str], None] = ('4ad0fb48ebe3', 'c3d9f2a4e6b7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
