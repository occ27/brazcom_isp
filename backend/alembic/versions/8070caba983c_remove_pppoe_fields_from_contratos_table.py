"""Remove PPPoE fields from servicos_contratados table

Revision ID: 8070caba983c
Revises: 5477db8f88ce
Create Date: 2025-11-27 17:25:20.051339

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8070caba983c'
down_revision: Union[str, Sequence[str], None] = '5477db8f88ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Remove PPPoE fields from servicos_contratados table
    op.drop_column('servicos_contratados', 'pppoe_username')
    op.drop_column('servicos_contratados', 'pppoe_password')
    op.drop_column('servicos_contratados', 'pppoe_service')
    op.drop_column('servicos_contratados', 'pppoe_profile')


def downgrade() -> None:
    """Downgrade schema."""
    # Add PPPoE fields back to servicos_contratados table
    op.add_column('servicos_contratados', sa.Column('pppoe_username', sa.String(50), nullable=True))
    op.add_column('servicos_contratados', sa.Column('pppoe_password', sa.String(50), nullable=True))
    op.add_column('servicos_contratados', sa.Column('pppoe_service', sa.String(50), nullable=True))
    op.add_column('servicos_contratados', sa.Column('pppoe_profile', sa.String(50), nullable=True))
