"""add receivables conditional

Revision ID: 9fae1b2c3d4e
Revises: 3b029419c891
Create Date: 2025-11-30 11:58:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9fae1b2c3d4e'
down_revision: Union[str, Sequence[str], None] = '3b029419c891'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(bind, table_name: str, schema: str = None) -> bool:
    """Check if table exists using SQLAlchemy inspector (DB-agnostic)."""
    try:
        inspector = sa.inspect(bind)
        return inspector.has_table(table_name)
    except Exception:
        return False


def upgrade() -> None:
    bind = op.get_bind()
    # Only create the table if it does not exist yet
    if not _table_exists(bind, 'receivables'):
        try:
            op.create_table(
            'receivables',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('empresa_id', sa.Integer(), nullable=False),
            sa.Column('cliente_id', sa.Integer(), nullable=False),
            sa.Column('servico_contratado_id', sa.Integer(), nullable=True),
            sa.Column('nfcom_fatura_id', sa.Integer(), nullable=True),

            sa.Column('tipo', sa.String(length=30), nullable=False, server_default='BOLETO'),

            sa.Column('issue_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('due_date', sa.DateTime(timezone=True), nullable=False),
            sa.Column('amount', sa.Float(), nullable=False),
            sa.Column('discount', sa.Float(), nullable=True, server_default='0.0'),
            sa.Column('interest_percent', sa.Float(), nullable=True, server_default='0.0'),
            sa.Column('fine_percent', sa.Float(), nullable=True, server_default='0.0'),

            # store bank/status as strings to keep migration simple
            sa.Column('bank', sa.String(length=50), nullable=False, server_default='SICOB'),
            sa.Column('carteira', sa.String(length=50), nullable=True),
            sa.Column('agencia', sa.String(length=20), nullable=True),
            sa.Column('conta', sa.String(length=50), nullable=True),
            sa.Column('nosso_numero', sa.String(length=100), nullable=True),
            sa.Column('bank_registration_id', sa.String(length=200), nullable=True),
            sa.Column('codigo_barras', sa.String(length=100), nullable=True),
            sa.Column('linha_digitavel', sa.String(length=200), nullable=True),

            sa.Column('status', sa.String(length=30), nullable=False, server_default='PENDING'),
            sa.Column('registered_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('printed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),

            sa.Column('registro_result', sa.Text(), nullable=True),
            sa.Column('pdf_url', sa.String(length=500), nullable=True),

            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),

            sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], ),
            sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id'], ),
            sa.ForeignKeyConstraint(['servico_contratado_id'], ['servicos_contratados.id'], ),
            sa.ForeignKeyConstraint(['nfcom_fatura_id'], ['nfcom_faturas.id'], ),
        )
        except Exception:
            # If table creation failed because the table already exists (race condition), skip silently
            pass
        else:
            op.create_index('ix_receivables_empresa_id', 'receivables', ['empresa_id'])
            op.create_index('ix_receivables_cliente_id', 'receivables', ['cliente_id'])
            op.create_index('ix_receivables_status', 'receivables', ['status'])


def downgrade() -> None:
    bind = op.get_bind()
    if _table_exists(bind, 'receivables'):
        op.drop_index('ix_receivables_status', table_name='receivables')
        op.drop_index('ix_receivables_cliente_id', table_name='receivables')
        op.drop_index('ix_receivables_empresa_id', table_name='receivables')
        op.drop_table('receivables')
