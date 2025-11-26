"""add_metodo_autenticacao_to_servicos_contratados

Revision ID: 60bf39ca466e
Revises: 8d4b9c68129e
Create Date: 2025-11-25 22:17:59.031002

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '60bf39ca466e'
down_revision: Union[str, Sequence[str], None] = '8d4b9c68129e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Adicionar coluna metodo_autenticacao como enum
    metodo_autenticacao_enum = sa.Enum('IP_MAC', 'PPPOE', 'HOTSPOT', 'RADIUS', name='metodoautenticacao')
    op.add_column('servicos_contratados', sa.Column('metodo_autenticacao', metodo_autenticacao_enum, nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remover coluna metodo_autenticacao
    op.drop_column('servicos_contratados', 'metodo_autenticacao')
    
    # Remover o enum se não estiver sendo usado em outro lugar
    metodo_autenticacao_enum = sa.Enum('IP_MAC', 'PPPOE', 'HOTSPOT', 'RADIUS', name='metodoautenticacao')
    metodo_autenticacao_enum.drop(op.get_bind(), checkfirst=True)
