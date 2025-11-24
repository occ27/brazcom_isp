"""merge all current heads

Revision ID: 20251124_merge_all_heads
Revises: 20251106_merge_heads_password_reset, 20251111_remove_vencimento_from_servicos_contratados, 20251119_add_email_status_fields_to_nfcom, 20251119_add_nfcom_email_columns, 20251124_add_access_control
Create Date: 2025-11-24 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251124_merge_all_heads'
down_revision: Union[str, Sequence[str], None] = ('20251106_merge_heads_password_reset', '20251111_remove_vencimento_from_servicos_contratados', '20251119_add_email_status_fields_to_nfcom', '20251119_add_nfcom_email_columns', '20251124_add_access_control')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass