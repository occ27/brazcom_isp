"""add_client_auth_fields

Revision ID: edf0d8ef7a09
Revises: 3cc016a1f611
Create Date: 2025-12-04 10:26:00.112348

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'edf0d8ef7a09'
down_revision: Union[str, Sequence[str], None] = '3cc016a1f611'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Adicionar campos de autenticação para clientes
    op.add_column('clientes', sa.Column('password_hash', sa.String(255), nullable=True))
    op.add_column('clientes', sa.Column('reset_token', sa.String(255), nullable=True))
    op.add_column('clientes', sa.Column('reset_token_expires', sa.DateTime(), nullable=True))
    op.add_column('clientes', sa.Column('email_verified', sa.Boolean(), nullable=True, default=False))
    op.add_column('clientes', sa.Column('last_login', sa.DateTime(), nullable=True))

    # Criar índice único composto para (empresa_id, cpf_cnpj)
    op.create_unique_constraint('uq_clientes_empresa_cpf_cnpj', 'clientes', ['empresa_id', 'cpf_cnpj'])


def downgrade() -> None:
    """Downgrade schema."""
    # Remover índice único
    op.drop_constraint('uq_clientes_empresa_cpf_cnpj', 'clientes', type_='unique')

    # Remover campos adicionados
    op.drop_column('clientes', 'last_login')
    op.drop_column('clientes', 'email_verified')
    op.drop_column('clientes', 'reset_token_expires')
    op.drop_column('clientes', 'reset_token')
    op.drop_column('clientes', 'password_hash')
