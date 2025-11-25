"""add_network_config_fields_to_servico_contratado

Revision ID: 8d4b9c68129e
Revises: 9c8c75845a9d
Create Date: 2025-11-25 18:18:19.357341

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8d4b9c68129e'
down_revision: Union[str, Sequence[str], None] = '9c8c75845a9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Configuração de rede (provisionamento automático)
    op.add_column('servicos_contratados', sa.Column('router_id', sa.Integer(), nullable=True))
    op.add_column('servicos_contratados', sa.Column('interface_id', sa.Integer(), nullable=True))
    op.add_column('servicos_contratados', sa.Column('ip_class_id', sa.Integer(), nullable=True))
    op.add_column('servicos_contratados', sa.Column('mac_address', sa.String(length=17), nullable=True))
    op.add_column('servicos_contratados', sa.Column('assigned_ip', sa.String(length=15), nullable=True))

    # Foreign keys
    op.create_foreign_key('fk_servicos_contratados_router_id', 'servicos_contratados', 'routers', ['router_id'], ['id'])
    op.create_foreign_key('fk_servicos_contratados_interface_id', 'servicos_contratados', 'router_interfaces', ['interface_id'], ['id'])
    op.create_foreign_key('fk_servicos_contratados_ip_class_id', 'servicos_contratados', 'ip_classes', ['ip_class_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Remove foreign keys primeiro
    op.drop_constraint('fk_servicos_contratados_ip_class_id', 'servicos_contratados', type_='foreignkey')
    op.drop_constraint('fk_servicos_contratados_interface_id', 'servicos_contratados', type_='foreignkey')
    op.drop_constraint('fk_servicos_contratados_router_id', 'servicos_contratados', type_='foreignkey')

    # Remove as colunas
    op.drop_column('servicos_contratados', 'assigned_ip')
    op.drop_column('servicos_contratados', 'mac_address')
    op.drop_column('servicos_contratados', 'ip_class_id')
    op.drop_column('servicos_contratados', 'interface_id')
    op.drop_column('servicos_contratados', 'router_id')
