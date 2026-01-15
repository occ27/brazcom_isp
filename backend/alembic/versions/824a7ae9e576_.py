"""empty message

Revision ID: 824a7ae9e576
Revises: add_sicredi_support_20251208, cccee317de58
Create Date: 2025-12-08 12:42:24.018365

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '824a7ae9e576'
down_revision: Union[str, Sequence[str], None] = ('add_sicredi_support_20251208', 'cccee317de58')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
