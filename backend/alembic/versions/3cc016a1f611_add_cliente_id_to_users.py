"""add cliente_id to users

Revision ID: 3cc016a1f611
Revises: 77e1ace25f87
Create Date: 2025-12-02 15:48:48.824534

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3cc016a1f611'
down_revision: Union[str, Sequence[str], None] = '77e1ace25f87'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Adicionar coluna cliente_id na tabela users
    op.add_column('users', sa.Column('cliente_id', sa.Integer(), sa.ForeignKey('clientes.id'), nullable=True))

    # Criar índice para performance
    op.create_index('ix_users_cliente_id', 'users', ['cliente_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Remover índice
    op.drop_index('ix_users_cliente_id')

    # Remover coluna
    op.drop_column('users', 'cliente_id')
