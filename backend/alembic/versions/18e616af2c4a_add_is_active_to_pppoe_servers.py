"""add_is_active_to_pppoe_servers

Revision ID: 18e616af2c4a
Revises: f509b29332e4
Create Date: 2025-11-27 12:57:11.580115

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '18e616af2c4a'
down_revision: Union[str, Sequence[str], None] = 'f509b29332e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Adicionar campo is_active à tabela pppoe_servers
    op.add_column('pppoe_servers', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remover campo is_active da tabela pppoe_servers
    op.drop_column('pppoe_servers', 'is_active')
