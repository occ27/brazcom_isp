"""add active_empresa_id to users

Revision ID: 2025_10_22_1030
Revises: 76213f19b622_update_empresa_fields_required_for_nfcom
Create Date: 2025-10-22 10:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2025_10_22_1030'
down_revision = '76213f19b622'
branch_labels = None
depends_on = None


def upgrade():
    # Add column active_empresa_id to users
    op.add_column('users', sa.Column('active_empresa_id', sa.Integer(), nullable=True))
    # Create foreign key constraint to empresas.id
    op.create_foreign_key(
        'fk_users_active_empresa', 'users', 'empresas', ['active_empresa_id'], ['id'], ondelete='SET NULL'
    )


def downgrade():
    # Drop foreign key and column
    op.drop_constraint('fk_users_active_empresa', 'users', type_='foreignkey')
    op.drop_column('users', 'active_empresa_id')
