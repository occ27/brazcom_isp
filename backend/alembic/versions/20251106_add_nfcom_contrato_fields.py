"""Add contract fields to nfcom table

Revision ID: 20251106_add_nfcom_contrato_fields
Revises: 20251105_servicos_contratados
Create Date: 2025-11-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251106_add_nfcom_contrato_fields'
down_revision: Union[str, Sequence[str], None] = '20251105_servicos_contratados'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add contract snapshot fields to nfcom."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = [c['name'] for c in inspector.get_columns('nfcom')] if 'nfcom' in inspector.get_table_names() else []

    if 'numero_contrato' not in cols:
        op.add_column('nfcom', sa.Column('numero_contrato', sa.String(length=50), nullable=True))
        # create index only if column was added
        op.create_index(op.f('ix_nfcom_numero_contrato'), 'nfcom', ['numero_contrato'], unique=False)

    if 'd_contrato_ini' not in cols:
        op.add_column('nfcom', sa.Column('d_contrato_ini', sa.Date(), nullable=True))

    if 'd_contrato_fim' not in cols:
        op.add_column('nfcom', sa.Column('d_contrato_fim', sa.Date(), nullable=True))


def downgrade() -> None:
    """Remove contract snapshot fields from nfcom."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = [c['name'] for c in inspector.get_columns('nfcom')] if 'nfcom' in inspector.get_table_names() else []

    if 'numero_contrato' in cols:
        try:
            op.drop_index(op.f('ix_nfcom_numero_contrato'), table_name='nfcom')
        except Exception:
            pass
        op.drop_column('nfcom', 'numero_contrato')

    if 'd_contrato_ini' in cols:
        op.drop_column('nfcom', 'd_contrato_ini')

    if 'd_contrato_fim' in cols:
        op.drop_column('nfcom', 'd_contrato_fim')
