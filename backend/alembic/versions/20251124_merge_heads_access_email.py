"""merge heads for access control and email jobs

Revision ID: 20251124_merge_heads_access_email
Revises: da0e3d37c8e8, 20251119_add_nfcom_email_jobs_and_statuses
Create Date: 2025-11-24 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251124_merge_heads_access_email'
down_revision: Union[str, Sequence[str], None] = ('da0e3d37c8e8', '20251119_add_nfcom_email_jobs_and_statuses')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass