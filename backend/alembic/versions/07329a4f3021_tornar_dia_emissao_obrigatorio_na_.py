"""Tornar dia_emissao obrigatorio na tabela servicos_contratados

Revision ID: 07329a4f3021
Revises: 20251105_servicos_contratados
Create Date: 2025-11-05 16:00:06.342705

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '07329a4f3021'
down_revision: Union[str, Sequence[str], None] = '20251105_servicos_contratados'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Primeiro, definir um valor padrão (dia 1) para registros existentes com dia_emissao NULL
    op.execute("UPDATE servicos_contratados SET dia_emissao = 1 WHERE dia_emissao IS NULL")
    
    # Alterar a coluna para NOT NULL
    op.alter_column('servicos_contratados', 'dia_emissao',
                    existing_type=sa.Integer(),
                    nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Reverter para nullable
    op.alter_column('servicos_contratados', 'dia_emissao',
                    existing_type=sa.Integer(),
                    nullable=True)
