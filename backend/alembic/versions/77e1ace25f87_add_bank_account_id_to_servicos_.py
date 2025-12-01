"""add_bank_account_id_to_servicos_contratados

Revision ID: 77e1ace25f87
Revises: e0da09cbd4bf
Create Date: 2025-12-01 11:18:08.851417

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '77e1ace25f87'
down_revision: Union[str, Sequence[str], None] = 'e0da09cbd4bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('servicos_contratados', sa.Column('bank_account_id', sa.Integer(), sa.ForeignKey('bank_accounts.id'), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('servicos_contratados', 'bank_account_id')
