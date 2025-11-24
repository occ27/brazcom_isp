"""Add user_id to empresas table with default value

Revision ID: 1354a8c1b570
Revises: df224ecc7d28
Create Date: 2025-10-22 02:22:07.022830

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1354a8c1b570'
down_revision: Union[str, Sequence[str], None] = 'df224ecc7d28'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add user_id column as nullable first
    op.add_column('empresas', sa.Column('user_id', sa.Integer(), nullable=True))
    
    # Update existing empresas with a default user ID (e.g., 1) where user_id is NULL
    # NOTE: This assumes a user with ID 1 exists. This is a common default.
    op.execute("UPDATE empresas SET user_id = 1 WHERE user_id IS NULL")
    
    # Now make the column non-nullable
    op.alter_column('empresas', 'user_id', nullable=False)
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_empresas_user_id', 'empresas', 'users', ['user_id'], ['id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    # It's good practice to name the constraint to drop it reliably
    op.drop_constraint('fk_empresas_user_id', 'empresas', type_='foreignkey')
    
    # Remove the column
    op.drop_column('empresas', 'user_id')