"""Add vencimento to servicos_contratados

Revision ID: 20251106_add_vencimento_servicos_contratados
Revises: 20251106_add_nfcom_contrato_fields
Create Date: 2025-11-06 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251106_add_vencimento_servicos_contratados'
down_revision: Union[str, Sequence[str], None] = '20251106_add_nfcom_contrato_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add vencimento column to servicos_contratados."""
    op.add_column('servicos_contratados', sa.Column('vencimento', sa.Date(), nullable=True))
    op.create_index(op.f('ix_servicos_contratados_vencimento'), 'servicos_contratados', ['vencimento'], unique=False)


def downgrade() -> None:
    """Remove vencimento column from servicos_contratados."""
    try:
        op.drop_index(op.f('ix_servicos_contratados_vencimento'), table_name='servicos_contratados')
    except Exception:
        pass
    op.drop_column('servicos_contratados', 'vencimento')
