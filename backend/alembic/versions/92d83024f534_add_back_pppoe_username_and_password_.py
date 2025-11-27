"""Add back PPPoE username and password fields to servicos_contratados

Revision ID: 92d83024f534
Revises: 8070caba983c
Create Date: 2025-11-27 17:29:37.568921

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '92d83024f534'
down_revision: Union[str, Sequence[str], None] = '8070caba983c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add back PPPoE username and password fields to servicos_contratados table
    op.add_column('servicos_contratados', sa.Column('pppoe_username', sa.String(50), nullable=True))
    op.add_column('servicos_contratados', sa.Column('pppoe_password', sa.String(50), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove PPPoE username and password fields from servicos_contratados table
    op.drop_column('servicos_contratados', 'pppoe_username')
    op.drop_column('servicos_contratados', 'pppoe_password')
