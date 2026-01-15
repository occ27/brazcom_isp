"""add_sicredi_support

Revision ID: add_sicredi_support_20251208
Revises: 
Create Date: 2025-12-08 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_sicredi_support_20251208'
down_revision = None  # Ajustar conforme necessário
branch_labels = None
depends_on = None


def upgrade():
    """
    Adiciona suporte ao banco SICREDI:
    - Adiciona SICREDI ao enum Bank
    - Adiciona campos de configuração específicos do SICREDI no BankAccount
    """
    
    # Adicionar SICREDI ao enum Bank
    # Para PostgreSQL, precisamos usar op.execute para alterar o enum
    # Para SQLite, isso não é necessário
    connection = op.get_bind()
    dialect_name = connection.dialect.name
    
    if dialect_name == 'postgresql':
        # PostgreSQL: Alterar enum
        op.execute("ALTER TYPE bank ADD VALUE IF NOT EXISTS 'SICREDI'")
    elif dialect_name == 'mysql':
        # MySQL: Alterar enum na coluna
        op.execute("""
            ALTER TABLE receivables 
            MODIFY COLUMN bank ENUM('SICOB', 'SICREDI', 'OUTRO') 
            NOT NULL DEFAULT 'SICOB'
        """)
    # SQLite não tem suporte nativo a ENUMs, então não precisa de alteração
    
    # Adicionar campos específicos do SICREDI no BankAccount
    op.add_column('bank_accounts', 
        sa.Column('sicredi_codigo_beneficiario', sa.String(20), nullable=True)
    )
    op.add_column('bank_accounts', 
        sa.Column('sicredi_posto', sa.String(2), nullable=True)
    )
    op.add_column('bank_accounts', 
        sa.Column('sicredi_byte_id', sa.String(1), nullable=True)
    )


def downgrade():
    """
    Remove suporte ao SICREDI:
    - Remove campos específicos do SICREDI
    - Remove SICREDI do enum Bank
    """
    
    # Remover campos do SICREDI
    op.drop_column('bank_accounts', 'sicredi_byte_id')
    op.drop_column('bank_accounts', 'sicredi_posto')
    op.drop_column('bank_accounts', 'sicredi_codigo_beneficiario')
    
    # Remover SICREDI do enum (complicado em alguns bancos)
    connection = op.get_bind()
    dialect_name = connection.dialect.name
    
    if dialect_name == 'mysql':
        # MySQL: Restaurar enum original
        op.execute("""
            ALTER TABLE receivables 
            MODIFY COLUMN bank ENUM('SICOB', 'OUTRO') 
            NOT NULL DEFAULT 'SICOB'
        """)
    # PostgreSQL e SQLite: downgrade de enum é complexo, deixar como está
    # Para produção, criar uma migration específica se necessário
