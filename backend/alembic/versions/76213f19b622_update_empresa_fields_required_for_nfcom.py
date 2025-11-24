"""update_empresa_fields_required_for_nfcom

Revision ID: 76213f19b622
Revises: 1354a8c1b570
Create Date: 2025-10-22 02:46:16.287552

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '76213f19b622'
down_revision: Union[str, Sequence[str], None] = '1354a8c1b570'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Alterar campos para NOT NULL conforme requisitos NFCom
    op.alter_column('empresas', 'endereco', nullable=False, existing_type=sa.String(255))
    op.alter_column('empresas', 'numero', nullable=False, existing_type=sa.String(20))
    op.alter_column('empresas', 'bairro', nullable=False, existing_type=sa.String(100))
    op.alter_column('empresas', 'municipio', nullable=False, existing_type=sa.String(100))
    op.alter_column('empresas', 'uf', nullable=False, existing_type=sa.String(2))
    op.alter_column('empresas', 'codigo_ibge', nullable=False, existing_type=sa.String(7))
    op.alter_column('empresas', 'cep', nullable=False, existing_type=sa.String(9))
    op.alter_column('empresas', 'email', nullable=False, existing_type=sa.String(255))


def downgrade() -> None:
    """Downgrade schema."""
    # Reverter alterações (voltar para nullable)
    op.alter_column('empresas', 'endereco', nullable=True, existing_type=sa.String(255))
    op.alter_column('empresas', 'numero', nullable=True, existing_type=sa.String(20))
    op.alter_column('empresas', 'bairro', nullable=True, existing_type=sa.String(100))
    op.alter_column('empresas', 'municipio', nullable=True, existing_type=sa.String(100))
    op.alter_column('empresas', 'uf', nullable=True, existing_type=sa.String(2))
    op.alter_column('empresas', 'codigo_ibge', nullable=True, existing_type=sa.String(7))
    op.alter_column('empresas', 'cep', nullable=True, existing_type=sa.String(9))
    op.alter_column('empresas', 'email', nullable=True, existing_type=sa.String(255))
