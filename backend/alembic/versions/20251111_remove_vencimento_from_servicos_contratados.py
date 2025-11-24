"""Remove vencimento from servicos_contratados

Revision ID: 20251111_remove_vencimento_from_servicos_contratados
Revises: 20251110_add_dia_vencimento_to_servicos_contratados
Create Date: 2025-11-10 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251111_remove_vencimento_from_servicos_contratados'
down_revision = '20251110_add_dia_vencimento_to_servicos_contratados'
branch_labels = None
depends_on = None


def upgrade():
    # Remove legacy vencimento date column from servicos_contratados
    try:
        op.drop_column('servicos_contratados', 'vencimento')
    except Exception:
        # Best-effort drop: some DBs may require different handling
        pass


def downgrade():
    # Recreate the vencimento column as Date (nullable) if rolling back
    op.add_column('servicos_contratados', sa.Column('vencimento', sa.Date(), nullable=True))
