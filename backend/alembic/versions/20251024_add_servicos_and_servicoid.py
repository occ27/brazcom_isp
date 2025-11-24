"""add servicos table and servico_id to nfcom_itens

Revision ID: 20251024_add_servicos
Revises: 
Create Date: 2025-10-24 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251024_add_servicos'
down_revision = '3b895b5c7c30'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Create servicos table only if it does not already exist
    if 'servicos' not in inspector.get_table_names():
        op.create_table(
            'servicos',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('empresa_id', sa.Integer(), nullable=True),
            sa.Column('codigo', sa.String(length=50), nullable=True),
            sa.Column('descricao', sa.String(length=255), nullable=False),
            sa.Column('unidade_medida', sa.String(length=10), nullable=True),
            sa.Column('valor_unitario', sa.Float(), nullable=True),
            sa.Column('cfop', sa.String(length=4), nullable=True),
            sa.Column('ncm', sa.String(length=8), nullable=True),
            sa.Column('base_calculo_icms_default', sa.Float(), nullable=True),
            sa.Column('aliquota_icms_default', sa.Float(), nullable=True),
            sa.Column('ativo', sa.Boolean(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        )

    # Add servico_id to nfcom_itens only if missing
    if 'nfcom_itens' in inspector.get_table_names():
        existing_cols = [c['name'] for c in inspector.get_columns('nfcom_itens')]
        if 'servico_id' not in existing_cols:
            op.add_column('nfcom_itens', sa.Column('servico_id', sa.Integer(), nullable=True))
            op.create_foreign_key('fk_nfcom_itens_servico', 'nfcom_itens', 'servicos', ['servico_id'], ['id'])


def downgrade():
    # Drop foreign key and column
    op.drop_constraint('fk_nfcom_itens_servico', 'nfcom_itens', type_='foreignkey')
    op.drop_column('nfcom_itens', 'servico_id')
    # Drop servicos table
    op.drop_table('servicos')
