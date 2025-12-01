"""add_billing_config_fields_to_bank_accounts

Revision ID: e0da09cbd4bf
Revises: 4a06203d5253
Create Date: 2025-12-01 11:13:50.381796

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e0da09cbd4bf'
down_revision: Union[str, Sequence[str], None] = '4a06203d5253'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Adicionar campos de configuração de cobrança às contas bancárias
    op.add_column('bank_accounts', sa.Column('multa_atraso_percentual', sa.Float(), nullable=True, default=2.0))
    op.add_column('bank_accounts', sa.Column('juros_atraso_percentual', sa.Float(), nullable=True, default=1.0))


def downgrade() -> None:
    """Downgrade schema."""
    # Remover campos de configuração de cobrança
    op.drop_column('bank_accounts', 'juros_atraso_percentual')
    op.drop_column('bank_accounts', 'multa_atraso_percentual')
