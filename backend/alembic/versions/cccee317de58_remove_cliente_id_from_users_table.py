"""remove cliente_id from users table

Revision ID: cccee317de58
Revises: b2c5b2adbcd3
Create Date: 2025-12-04 11:36:27.235757

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cccee317de58'
down_revision: Union[str, Sequence[str], None] = 'b2c5b2adbcd3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Verificar e remover foreign key constraint
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    fks = inspector.get_foreign_keys('users')
    for fk in fks:
        if fk['constrained_columns'] == ['cliente_id']:
            op.drop_constraint(fk['name'], 'users', type_='foreignkey')
            break

    # Verificar se o índice existe antes de tentar removê-lo
    indexes = inspector.get_indexes('users')
    index_names = [idx['name'] for idx in indexes]
    
    if 'ix_users_cliente_id' in index_names:
        op.drop_index('ix_users_cliente_id', 'users')

    # Remover coluna
    op.drop_column('users', 'cliente_id')


def downgrade() -> None:
    """Downgrade schema."""
    # Adicionar coluna cliente_id na tabela users
    op.add_column('users', sa.Column('cliente_id', sa.Integer(), nullable=True))

    # Adicionar foreign key constraint
    op.create_foreign_key('fk_users_cliente_id', 'users', 'clientes', ['cliente_id'], ['id'])

    # Criar índice para performance
    op.create_index('ix_users_cliente_id', 'users', ['cliente_id'])
