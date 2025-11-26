"""change_default_contract_status_to_pending_installation

Revision ID: a5da2642e89b
Revises: 60bf39ca466e
Create Date: 2025-11-25 22:53:50.702959

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5da2642e89b'
down_revision: Union[str, Sequence[str], None] = '60bf39ca466e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Alterar o valor padrão da coluna status para PENDENTE_INSTALACAO
    op.alter_column('servicos_contratados', 'status',
                    existing_type=sa.String(length=20),
                    server_default='PENDENTE_INSTALACAO')


def downgrade() -> None:
    """Downgrade schema."""
    # Reverter o valor padrão para ATIVO
    op.alter_column('servicos_contratados', 'status',
                    existing_type=sa.String(length=20),
                    server_default='ATIVO')
