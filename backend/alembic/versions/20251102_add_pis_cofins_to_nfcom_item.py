"""Add pis cofins to nfcom item

Revision ID: 20251102_pis_cofins
Revises: 20251101_xml_fields
Create Date: 2025-11-02 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251102_pis_cofins'
down_revision: Union[str, Sequence[str], None] = '8a7d6e5c4f3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('nfcom_itens', sa.Column('base_calculo_pis', sa.Float(), nullable=True))
    op.add_column('nfcom_itens', sa.Column('aliquota_pis', sa.Float(), nullable=True))
    op.add_column('nfcom_itens', sa.Column('base_calculo_cofins', sa.Float(), nullable=True))
    op.add_column('nfcom_itens', sa.Column('aliquota_cofins', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('nfcom_itens', 'aliquota_cofins')
    op.drop_column('nfcom_itens', 'base_calculo_cofins')
    op.drop_column('nfcom_itens', 'aliquota_pis')
    op.drop_column('nfcom_itens', 'base_calculo_pis')
