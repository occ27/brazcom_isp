"""add_password_reset_tokens_cliente_table

Revision ID: 74e3bc6bd216
Revises: edf0d8ef7a09
Create Date: 2025-12-04 10:31:59.276344

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '74e3bc6bd216'
down_revision: Union[str, Sequence[str], None] = 'edf0d8ef7a09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create password_reset_tokens_cliente table
    op.create_table('password_reset_tokens_cliente',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cliente_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    # Create index on code column
    op.create_index(op.f('ix_password_reset_tokens_cliente_code'), 'password_reset_tokens_cliente', ['code'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index and table
    op.drop_index(op.f('ix_password_reset_tokens_cliente_code'), table_name='password_reset_tokens_cliente')
    op.drop_table('password_reset_tokens_cliente')
