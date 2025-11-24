"""Add servicos_contratados table

Revision ID: 20251105_servicos_contratados
Revises: 20251102_pis_cofins
Create Date: 2025-11-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251105_servicos_contratados'
down_revision: Union[str, Sequence[str], None] = '20251102_pis_cofins'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create servicos_contratados."""
    op.create_table(
        'servicos_contratados',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('empresa_id', sa.Integer(), nullable=False),
        sa.Column('cliente_id', sa.Integer(), nullable=False),
        sa.Column('servico_id', sa.Integer(), nullable=False),

        sa.Column('numero_contrato', sa.String(length=50), nullable=True),
        sa.Column('d_contrato_ini', sa.Date(), nullable=True),
        sa.Column('d_contrato_fim', sa.Date(), nullable=True),

        sa.Column('periodicidade', sa.String(length=20), nullable=False, server_default='MENSAL'),
        sa.Column('dia_emissao', sa.Integer(), nullable=True),
        sa.Column('quantidade', sa.Float(), nullable=False),
        sa.Column('valor_unitario', sa.Float(), nullable=False),
        sa.Column('valor_total', sa.Float(), nullable=True),

        sa.Column('auto_emit', sa.Boolean(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('last_emission', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_emission', sa.DateTime(timezone=True), nullable=True),

        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),

        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], ),
        sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id'], ),
        sa.ForeignKeyConstraint(['servico_id'], ['servicos.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_servicos_contratados_empresa_id'), 'servicos_contratados', ['empresa_id'], unique=False)
    op.create_index(op.f('ix_servicos_contratados_cliente_id'), 'servicos_contratados', ['cliente_id'], unique=False)
    op.create_index(op.f('ix_servicos_contratados_servico_id'), 'servicos_contratados', ['servico_id'], unique=False)
    # Índice composto útil para buscas do job de agendamento
    op.create_index(op.f('ix_servicos_contratados_agendamento'), 'servicos_contratados', ['empresa_id', 'is_active', 'next_emission'], unique=False)


def downgrade() -> None:
    """Downgrade schema: drop servicos_contratados."""
    op.drop_index(op.f('ix_servicos_contratados_agendamento'), table_name='servicos_contratados')
    op.drop_index(op.f('ix_servicos_contratados_servico_id'), table_name='servicos_contratados')
    op.drop_index(op.f('ix_servicos_contratados_cliente_id'), table_name='servicos_contratados')
    op.drop_index(op.f('ix_servicos_contratados_empresa_id'), table_name='servicos_contratados')
    op.drop_table('servicos_contratados')
