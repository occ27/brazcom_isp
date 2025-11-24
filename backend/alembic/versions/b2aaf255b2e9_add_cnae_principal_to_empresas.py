"""add_cnae_principal_to_empresas

Revision ID: b2aaf255b2e9
Revises: 76213f19b622
Create Date: 2025-10-22 02:50:24.916932

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2aaf255b2e9'
down_revision: Union[str, Sequence[str], None] = '76213f19b622'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('empresas', sa.Column('cnae_principal', sa.String(10), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('empresas', 'cnae_principal')
