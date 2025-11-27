"""add_empresa_id_router_id_to_dhcp_networks

Revision ID: 20251127_1149
Revises: 563d00fb4cb0
Create Date: 2025-11-27 11:49:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251127_1149'
down_revision: Union[str, Sequence[str], None] = '563d00fb4cb0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Adicionar colunas empresa_id e router_id à tabela dhcp_networks
    op.add_column('dhcp_networks', sa.Column('empresa_id', sa.Integer(), nullable=False))
    op.add_column('dhcp_networks', sa.Column('router_id', sa.Integer(), nullable=True))

    # Criar foreign keys
    op.create_foreign_key(
        'fk_dhcp_networks_empresa_id',
        'dhcp_networks', 'empresas',
        ['empresa_id'], ['id']
    )
    op.create_foreign_key(
        'fk_dhcp_networks_router_id',
        'dhcp_networks', 'routers',
        ['router_id'], ['id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remover foreign keys
    op.drop_constraint('fk_dhcp_networks_router_id', 'dhcp_networks', type_='foreignkey')
    op.drop_constraint('fk_dhcp_networks_empresa_id', 'dhcp_networks', type_='foreignkey')

    # Remover colunas
    op.drop_column('dhcp_networks', 'router_id')
    op.drop_column('dhcp_networks', 'empresa_id')