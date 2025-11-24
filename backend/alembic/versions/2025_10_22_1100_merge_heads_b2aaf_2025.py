"""merge heads b2aaf255b2e9 and 2025_10_22_1030

Revision ID: 2025_10_22_1100
Revises: b2aaf255b2e9, 2025_10_22_1030
Create Date: 2025-10-22 11:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2025_10_22_1100'
down_revision = ('b2aaf255b2e9', '2025_10_22_1030')
branch_labels = None
depends_on = None


def upgrade():
    # merge migration - no DB ops required
    pass


def downgrade():
    # nothing to do on downgrade for merge
    pass
