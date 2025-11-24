"""Add empresa_clientes and empresa_cliente_enderecos tables and migrate existing data

Revision ID: c3d9f2a4e6b7
Revises: 2025_10_22_1100
Create Date: 2025-10-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String, Integer, Boolean, DateTime

# revision identifiers, used by Alembic.
revision = 'c3d9f2a4e6b7'
down_revision = '2025_10_22_1100'
branch_labels = None
depends_on = None


def upgrade():
    # Create empresa_clientes table
    op.create_table(
        'empresa_clientes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('empresa_id', sa.Integer(), sa.ForeignKey('empresas.id'), nullable=False),
        sa.Column('cliente_id', sa.Integer(), sa.ForeignKey('clientes.id'), nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.sql.expression.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Create empresa_cliente_enderecos table
    op.create_table(
        'empresa_cliente_enderecos',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('empresa_cliente_id', sa.Integer(), sa.ForeignKey('empresa_clientes.id'), nullable=False),
        sa.Column('descricao', sa.String(100), nullable=True),
        sa.Column('endereco', sa.String(255), nullable=False),
        sa.Column('numero', sa.String(20), nullable=False),
        sa.Column('complemento', sa.String(100), nullable=True),
        sa.Column('bairro', sa.String(100), nullable=False),
        sa.Column('municipio', sa.String(100), nullable=False),
        sa.Column('uf', sa.String(2), nullable=False),
        sa.Column('cep', sa.String(9), nullable=False),
        sa.Column('codigo_ibge', sa.String(7), nullable=True),
        sa.Column('is_principal', sa.Boolean(), nullable=True, server_default=sa.sql.expression.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # Migrate existing clients -> empresa_clientes
    # For legacy Cliente rows that reference empresa_id, create a matching empresa_clientes row
    op.execute("""
    INSERT INTO empresa_clientes (empresa_id, cliente_id, created_by_user_id, is_active, created_at, updated_at)
    SELECT c.empresa_id, c.id, e.user_id, c.is_active, c.created_at, c.updated_at
    FROM clientes c
    JOIN empresas e ON e.id = c.empresa_id
    WHERE c.empresa_id IS NOT NULL
    """)

    # Migrate existing cliente_enderecos -> empresa_cliente_enderecos
    # Map cliente -> empresa_clientes by (cliente_id, empresa_id)
    op.execute("""
    INSERT INTO empresa_cliente_enderecos (empresa_cliente_id, descricao, endereco, numero, complemento, bairro, municipio, uf, cep, codigo_ibge, is_principal, created_at)
    SELECT ec.id as empresa_cliente_id,
           ce.descricao,
           ce.endereco,
           ce.numero,
           ce.complemento,
           ce.bairro,
           ce.municipio,
           ce.uf,
           ce.cep,
           NULL as codigo_ibge,
           ce.is_principal,
           ce.created_at
    FROM cliente_enderecos ce
    JOIN clientes c ON ce.cliente_id = c.id
    JOIN empresa_clientes ec ON ec.cliente_id = c.id AND ec.empresa_id = c.empresa_id
    """)


def downgrade():
    # Move addresses back to cliente_enderecos (best-effort) before dropping tables
    op.execute("""
    INSERT INTO cliente_enderecos (cliente_id, descricao, endereco, numero, complemento, bairro, municipio, uf, cep, is_principal, created_at)
    SELECT ec.cliente_id,
           ece.descricao,
           ece.endereco,
           ece.numero,
           ece.complemento,
           ece.bairro,
           ece.municipio,
           ece.uf,
           ece.cep,
           ece.is_principal,
           ece.created_at
    FROM empresa_cliente_enderecos ece
    JOIN empresa_clientes ec ON ece.empresa_cliente_id = ec.id
    """)

    # Remove migrated empresa_clientes rows (leave clientes table intact)
    op.execute("""
    DELETE FROM empresa_clientes WHERE id IN (SELECT id FROM empresa_clientes)
    """)

    # Drop the tables
    op.drop_table('empresa_cliente_enderecos')
    op.drop_table('empresa_clientes')
