"""Add xml_url to nfcom table

Revision ID: 8a7d6e5c4f3b
Revises: 50db718178e9
Create Date: 2025-10-28 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a7d6e5c4f3b'
down_revision: Union[str, Sequence[str], None] = '50db718178e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('nfcom', sa.Column('xml_url', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('nfcom', 'xml_url')