"""Add password_reset_tokens table

Revision ID: 20251106_add_password_reset_tokens
Revises: 20251106_add_vencimento_servicos_contratados
Create Date: 2025-11-06 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251106_add_password_reset_tokens'
down_revision: Union[str, Sequence[str], None] = '20251106_add_vencimento_servicos_contratados'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create password_reset_tokens table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'password_reset_tokens' not in inspector.get_table_names():
        op.create_table(
            'password_reset_tokens',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('usuario_id', sa.Integer(), nullable=False),
            sa.Column('code', sa.String(length=20), nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('used', sa.Boolean(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),

            sa.ForeignKeyConstraint(['usuario_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_password_reset_tokens_usuario_id'), 'password_reset_tokens', ['usuario_id'], unique=False)
        op.create_index(op.f('ix_password_reset_tokens_code'), 'password_reset_tokens', ['code'], unique=False)


def downgrade() -> None:
    """Drop password_reset_tokens table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'password_reset_tokens' in inspector.get_table_names():
        try:
            op.drop_index(op.f('ix_password_reset_tokens_code'), table_name='password_reset_tokens')
        except Exception:
            pass
        try:
            op.drop_index(op.f('ix_password_reset_tokens_usuario_id'), table_name='password_reset_tokens')
        except Exception:
            pass
        op.drop_table('password_reset_tokens')
