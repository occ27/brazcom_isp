"""add_isp_specific_fields_to_servico_contratado

Revision ID: 458b6df5c30c
Revises: 3e3812829058
Create Date: 2025-11-25 13:51:24.256248

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '458b6df5c30c'
down_revision: Union[str, Sequence[str], None] = '3e3812829058'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Status do contrato
    op.add_column('servicos_contratados', sa.Column('status', sa.String(length=20), nullable=False, server_default='ATIVO'))

    # Informações de instalação
    op.add_column('servicos_contratados', sa.Column('endereco_instalacao', sa.Text(), nullable=True))
    op.add_column('servicos_contratados', sa.Column('tipo_conexao', sa.String(length=30), nullable=True))
    op.add_column('servicos_contratados', sa.Column('coordenadas_gps', sa.String(length=50), nullable=True))
    op.add_column('servicos_contratados', sa.Column('data_instalacao', sa.Date(), nullable=True))
    op.add_column('servicos_contratados', sa.Column('responsavel_tecnico', sa.String(length=100), nullable=True))

    # Campos de cobrança adicionais
    op.add_column('servicos_contratados', sa.Column('periodo_carencia', sa.Integer(), nullable=True, default=0))
    op.add_column('servicos_contratados', sa.Column('multa_atraso_percentual', sa.Float(), nullable=True, default=0.0))

    # Taxas adicionais
    op.add_column('servicos_contratados', sa.Column('taxa_instalacao', sa.Float(), nullable=True, default=0.0))
    op.add_column('servicos_contratados', sa.Column('taxa_instalacao_paga', sa.Boolean(), nullable=True, default=False))

    # SLA e qualidade
    op.add_column('servicos_contratados', sa.Column('sla_garantido', sa.Float(), nullable=True))
    op.add_column('servicos_contratados', sa.Column('velocidade_garantida', sa.String(length=50), nullable=True))

    # Relacionamento com subscription ativa
    op.add_column('servicos_contratados', sa.Column('subscription_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_servicos_contratados_subscription_id', 'servicos_contratados', 'subscriptions', ['subscription_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Remove foreign key primeiro
    op.drop_constraint('fk_servicos_contratados_subscription_id', 'servicos_contratados', type_='foreignkey')

    # Remove as colunas na ordem inversa
    op.drop_column('servicos_contratados', 'subscription_id')
    op.drop_column('servicos_contratados', 'velocidade_garantida')
    op.drop_column('servicos_contratados', 'sla_garantido')
    op.drop_column('servicos_contratados', 'taxa_instalacao_paga')
    op.drop_column('servicos_contratados', 'taxa_instalacao')
    op.drop_column('servicos_contratados', 'multa_atraso_percentual')
    op.drop_column('servicos_contratados', 'periodo_carencia')
    op.drop_column('servicos_contratados', 'responsavel_tecnico')
    op.drop_column('servicos_contratados', 'data_instalacao')
    op.drop_column('servicos_contratados', 'coordenadas_gps')
    op.drop_column('servicos_contratados', 'tipo_conexao')
    op.drop_column('servicos_contratados', 'endereco_instalacao')
    op.drop_column('servicos_contratados', 'status')
