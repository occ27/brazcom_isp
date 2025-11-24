"""add access control tables

Revision ID: 20251124_add_access_control
Revises: 20251124_merge_heads_access_email
Create Date: 2025-11-24 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251124_add_access_control'
down_revision = '20251124_merge_heads_access_email'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('description', sa.String(255)),
        sa.Column('empresa_id', sa.Integer, sa.ForeignKey('empresas.id'), nullable=True),
    )

    op.create_table(
        'permissions',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.String(255)),
    )

    op.create_table(
        'role_permission_association',
        sa.Column('role_id', sa.Integer, sa.ForeignKey('roles.id'), primary_key=True),
        sa.Column('permission_id', sa.Integer, sa.ForeignKey('permissions.id'), primary_key=True),
    )

    op.create_table(
        'user_role_association',
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('role_id', sa.Integer, sa.ForeignKey('roles.id'), primary_key=True),
        sa.Column('empresa_id', sa.Integer, sa.ForeignKey('empresas.id'), nullable=True),
    )


def downgrade():
    op.drop_table('user_role_association')
    op.drop_table('role_permission_association')
    op.drop_table('permissions')
    op.drop_table('roles')
