"""add_pppoe_fields_to_servicos_contratados

Revision ID: c5475180b907
Revises: 18e616af2c4a
Create Date: 2025-11-27 15:55:12.762991

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5475180b907'
down_revision: Union[str, Sequence[str], None] = '18e616af2c4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Adicionar campos PPPoE à tabela servicos_contratados
    op.add_column('servicos_contratados', sa.Column('pppoe_username', sa.String(50), nullable=True, comment='Username PPPoE do cliente'))
    op.add_column('servicos_contratados', sa.Column('pppoe_password', sa.String(50), nullable=True, comment='Password PPPoE do cliente'))
    op.add_column('servicos_contratados', sa.Column('pppoe_service', sa.String(50), nullable=True, comment='Nome do serviço PPPoE'))
    op.add_column('servicos_contratados', sa.Column('pppoe_profile', sa.String(50), nullable=True, comment='Profile PPPoE a ser usado'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remover campos PPPoE da tabela servicos_contratados
    op.drop_column('servicos_contratados', 'pppoe_profile')
    op.drop_column('servicos_contratados', 'pppoe_service')
    op.drop_column('servicos_contratados', 'pppoe_password')
    op.drop_column('servicos_contratados', 'pppoe_username')
