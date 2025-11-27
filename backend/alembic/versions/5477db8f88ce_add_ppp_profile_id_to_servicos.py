"""add_ppp_profile_id_to_servicos

Revision ID: 5477db8f88ce
Revises: c5475180b907
Create Date: 2025-11-27 16:15:48.679669

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5477db8f88ce'
down_revision: Union[str, Sequence[str], None] = 'c5475180b907'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Adicionar coluna ppp_profile_id à tabela servicos
    op.add_column('servicos', sa.Column('ppp_profile_id', sa.Integer(), sa.ForeignKey('ppp_profiles.id'), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remover coluna ppp_profile_id da tabela servicos
    op.drop_column('servicos', 'ppp_profile_id')
