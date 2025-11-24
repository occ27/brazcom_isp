"""Add dia_vencimento to servicos_contratados

Revision ID: 20251110_add_dia_vencimento_to_servicos_contratados
Revises: 20251106_add_vencimento_servicos_contratados
Create Date: 2025-11-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251110_add_dia_vencimento_to_servicos_contratados'
down_revision = '20251106_add_vencimento_servicos_contratados'
branch_labels = None
depends_on = None


def upgrade():
    # Add new integer column for day of month
    op.add_column('servicos_contratados', sa.Column('dia_vencimento', sa.Integer(), nullable=True))
    # If there are existing 'vencimento' date values, migrate the day component
    conn = op.get_bind()
    try:
        conn.execute(sa.text("""
            UPDATE servicos_contratados
            SET dia_vencimento = EXTRACT(DAY FROM vencimento)::integer
            WHERE vencimento IS NOT NULL
        """))
    except Exception:
        # Best-effort migration; if DB does not support EXTRACT or cast syntax, ignore
        pass
    # Create an index on dia_vencimento for faster filtering
    op.create_index(op.f('ix_servicos_contratados_dia_vencimento'), 'servicos_contratados', ['dia_vencimento'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_servicos_contratados_dia_vencimento'), table_name='servicos_contratados')
    op.drop_column('servicos_contratados', 'dia_vencimento')
