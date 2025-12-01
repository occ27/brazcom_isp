"""add_sicoob_credentials_fields

Revision ID: 4a06203d5253
Revises: a1b2c3d4e5
Create Date: 2025-12-01 10:44:19.200700

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a06203d5253'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Adicionar campos para credenciais do Sicoob
    op.add_column('bank_accounts', sa.Column('sicoob_client_id', sa.String(length=100), nullable=True))
    op.add_column('bank_accounts', sa.Column('sicoob_access_token', sa.String(length=200), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remover campos das credenciais do Sicoob
    op.drop_column('bank_accounts', 'sicoob_access_token')
    op.drop_column('bank_accounts', 'sicoob_client_id')
