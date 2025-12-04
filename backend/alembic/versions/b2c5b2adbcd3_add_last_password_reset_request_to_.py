"""add_last_password_reset_request_to_cliente

Revision ID: b2c5b2adbcd3
Revises: 74e3bc6bd216
Create Date: 2025-12-04 11:00:57.750526

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c5b2adbcd3'
down_revision: Union[str, Sequence[str], None] = '74e3bc6bd216'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Adicionar campo last_password_reset_request à tabela clientes
    op.add_column('clientes', sa.Column('last_password_reset_request', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remover campo last_password_reset_request da tabela clientes
    op.drop_column('clientes', 'last_password_reset_request')
