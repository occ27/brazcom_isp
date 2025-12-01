"""add receivable bank columns

Revision ID: add_receivable_bank_columns_20251130
Revises: 9fae1b2c3d4e
Create Date: 2025-11-30 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5'
down_revision = '9fae1b2c3d4e'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c['name'] for c in inspector.get_columns('receivables')} if inspector.has_table('receivables') else set()

    if 'bank_account_id' not in cols:
        op.add_column('receivables', sa.Column('bank_account_id', sa.Integer(), nullable=True))
        # create fk if bank_accounts table exists
        if inspector.has_table('bank_accounts'):
            op.create_foreign_key(
                'fk_receivables_bank_account_id', 'receivables', 'bank_accounts', ['bank_account_id'], ['id']
            )

    if 'bank_account_snapshot' not in cols:
        op.add_column('receivables', sa.Column('bank_account_snapshot', sa.Text(), nullable=True))

    if 'bank_payload' not in cols:
        op.add_column('receivables', sa.Column('bank_payload', sa.Text(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table('receivables'):
        cols = {c['name'] for c in inspector.get_columns('receivables')}
        if 'bank_payload' in cols:
            op.drop_column('receivables', 'bank_payload')
        if 'bank_account_snapshot' in cols:
            op.drop_column('receivables', 'bank_account_snapshot')
        if 'bank_account_id' in cols:
            # drop fk if exists
            try:
                op.drop_constraint('fk_receivables_bank_account_id', 'receivables', type_='foreignkey')
            except Exception:
                pass
            op.drop_column('receivables', 'bank_account_id')
