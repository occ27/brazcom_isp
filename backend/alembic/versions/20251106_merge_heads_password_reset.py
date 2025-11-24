"""merge heads for password reset migration

Revision ID: 20251106_merge_heads_password_reset
Revises: 07329a4f3021, 20251106_add_password_reset_tokens
Create Date: 2025-11-06 13:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251106_merge_heads_password_reset'
down_revision: Union[str, Sequence[str], None] = ('07329a4f3021', '20251106_add_password_reset_tokens')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge heads - no schema changes."""
    pass


def downgrade() -> None:
    """Downgrade - no schema changes."""
    pass
