"""add_pppoe_dhcp_models

Revision ID: 563d00fb4cb0
Revises: a5da2642e89b
Create Date: 2025-11-26 17:17:05.678753

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '563d00fb4cb0'
down_revision: Union[str, Sequence[str], None] = 'a5da2642e89b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Criar tabela ip_pools
    op.create_table('ip_pools',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('ranges', sa.Text(), nullable=False),
        sa.Column('comentario', sa.Text(), nullable=True),
        sa.Column('empresa_id', sa.Integer(), nullable=False),
        sa.Column('router_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], ),
        sa.ForeignKeyConstraint(['router_id'], ['routers.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nome')
    )
    op.create_index(op.f('ix_ip_pools_id'), 'ip_pools', ['id'], unique=False)

    # Criar tabela ppp_profiles
    op.create_table('ppp_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('local_address', sa.String(length=15), nullable=False),
        sa.Column('remote_address_pool_id', sa.Integer(), nullable=True),
        sa.Column('rate_limit', sa.String(length=50), nullable=True),
        sa.Column('session_timeout', sa.String(length=20), nullable=True),
        sa.Column('idle_timeout', sa.String(length=20), nullable=True),
        sa.Column('only_one_session', sa.Boolean(), nullable=True),
        sa.Column('comentario', sa.Text(), nullable=True),
        sa.Column('empresa_id', sa.Integer(), nullable=False),
        sa.Column('router_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], ),
        sa.ForeignKeyConstraint(['remote_address_pool_id'], ['ip_pools.id'], ),
        sa.ForeignKeyConstraint(['router_id'], ['routers.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nome')
    )
    op.create_index(op.f('ix_ppp_profiles_id'), 'ppp_profiles', ['id'], unique=False)

    # Criar tabela pppoe_servers
    op.create_table('pppoe_servers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('service_name', sa.String(length=100), nullable=False),
        sa.Column('interface_id', sa.Integer(), nullable=False),
        sa.Column('default_profile_id', sa.Integer(), nullable=False),
        sa.Column('max_sessions', sa.Integer(), nullable=True),
        sa.Column('max_sessions_per_host', sa.Integer(), nullable=True),
        sa.Column('authentication', sa.String(length=100), nullable=True),
        sa.Column('keepalive_timeout', sa.String(length=20), nullable=True),
        sa.Column('comentario', sa.Text(), nullable=True),
        sa.Column('empresa_id', sa.Integer(), nullable=False),
        sa.Column('router_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['default_profile_id'], ['ppp_profiles.id'], ),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], ),
        sa.ForeignKeyConstraint(['interface_id'], ['router_interfaces.id'], ),
        sa.ForeignKeyConstraint(['router_id'], ['routers.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('service_name')
    )
    op.create_index(op.f('ix_pppoe_servers_id'), 'pppoe_servers', ['id'], unique=False)

    # Criar tabela dhcp_servers
    op.create_table('dhcp_servers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('interface_id', sa.Integer(), nullable=False),
        sa.Column('address_pool_id', sa.Integer(), nullable=False),
        sa.Column('lease_time', sa.String(length=20), nullable=True),
        sa.Column('bootp_support', sa.String(length=10), nullable=True),
        sa.Column('comentario', sa.Text(), nullable=True),
        sa.Column('empresa_id', sa.Integer(), nullable=False),
        sa.Column('router_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['address_pool_id'], ['ip_pools.id'], ),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], ),
        sa.ForeignKeyConstraint(['interface_id'], ['router_interfaces.id'], ),
        sa.ForeignKeyConstraint(['router_id'], ['routers.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nome')
    )
    op.create_index(op.f('ix_dhcp_servers_id'), 'dhcp_servers', ['id'], unique=False)

    # Criar tabela dhcp_networks
    op.create_table('dhcp_networks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('dhcp_server_id', sa.Integer(), nullable=False),
        sa.Column('address', sa.String(length=18), nullable=False),
        sa.Column('gateway', sa.String(length=15), nullable=True),
        sa.Column('dns_servers', sa.String(length=255), nullable=True),
        sa.Column('domain', sa.String(length=100), nullable=True),
        sa.Column('wins_servers', sa.String(length=255), nullable=True),
        sa.Column('ntp_servers', sa.String(length=255), nullable=True),
        sa.Column('caps_manager', sa.String(length=255), nullable=True),
        sa.Column('comentario', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['dhcp_server_id'], ['dhcp_servers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dhcp_networks_id'), 'dhcp_networks', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Remover tabelas na ordem inversa
    op.drop_index(op.f('ix_dhcp_networks_id'), table_name='dhcp_networks')
    op.drop_table('dhcp_networks')
    op.drop_index(op.f('ix_dhcp_servers_id'), table_name='dhcp_servers')
    op.drop_table('dhcp_servers')
    op.drop_index(op.f('ix_pppoe_servers_id'), table_name='pppoe_servers')
    op.drop_table('pppoe_servers')
    op.drop_index(op.f('ix_ppp_profiles_id'), table_name='ppp_profiles')
    op.drop_table('ppp_profiles')
    op.drop_index(op.f('ix_ip_pools_id'), table_name='ip_pools')
    op.drop_table('ip_pools')
