"""extend servicos add nfcom fields

Revision ID: 20251025_extend_servicos_add_nfcom_fields
Revises: 
Create Date: 2025-10-25 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = '20251025_extend_servicos_add_nfcom_fields'
down_revision = '20251024_add_servicos'
branch_labels = None
depends_on = None


def _column_exists(connection, table_name, column_name):
    inspector = Inspector.from_engine(connection)
    cols = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in cols


def upgrade():
    conn = op.get_bind()
    table = 'servicos'
    # Add columns if they don't exist
    if not _column_exists(conn, table, 'cClass'):
        op.add_column(table, sa.Column('cClass', sa.String(length=7), nullable=False, server_default=''))
    if not _column_exists(conn, table, 'cfop'):
        op.add_column(table, sa.Column('cfop', sa.String(length=4), nullable=True))
    if not _column_exists(conn, table, 'ncm'):
        op.add_column(table, sa.Column('ncm', sa.String(length=8), nullable=True))
    if not _column_exists(conn, table, 'base_calculo_icms_default'):
        op.add_column(table, sa.Column('base_calculo_icms_default', sa.Float(), nullable=True))
    if not _column_exists(conn, table, 'aliquota_icms_default'):
        op.add_column(table, sa.Column('aliquota_icms_default', sa.Float(), nullable=True))
    if not _column_exists(conn, table, 'valor_desconto_default'):
        op.add_column(table, sa.Column('valor_desconto_default', sa.Float(), nullable=True, server_default='0'))
    if not _column_exists(conn, table, 'valor_outros_default'):
        op.add_column(table, sa.Column('valor_outros_default', sa.Float(), nullable=True, server_default='0'))


def downgrade():
    conn = op.get_bind()
    table = 'servicos'
    if _column_exists(conn, table, 'valor_outros_default'):
        op.drop_column(table, 'valor_outros_default')
    if _column_exists(conn, table, 'valor_desconto_default'):
        op.drop_column(table, 'valor_desconto_default')
    if _column_exists(conn, table, 'aliquota_icms_default'):
        op.drop_column(table, 'aliquota_icms_default')
    if _column_exists(conn, table, 'base_calculo_icms_default'):
        op.drop_column(table, 'base_calculo_icms_default')
    if _column_exists(conn, table, 'ncm'):
        op.drop_column(table, 'ncm')
    if _column_exists(conn, table, 'cfop'):
        op.drop_column(table, 'cfop')
    if _column_exists(conn, table, 'cClass'):
        op.drop_column(table, 'cClass')
