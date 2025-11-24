"""add nfcom email columns

Revision ID: 20251119_add_nfcom_email_columns
Revises: 20251119_add_nfcom_email_jobs_and_statuses
Create Date: 2025-11-19 00:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251119_add_nfcom_email_columns'
down_revision = '20251119_add_nfcom_email_jobs_and_statuses'
branch_labels = None
depends_on = None


def upgrade():
    # Add email tracking columns to nfcom table if not present
    conn = op.get_bind()
    # MySQL 8 supports IF NOT EXISTS
    op.execute("""
    ALTER TABLE nfcom
      ADD COLUMN IF NOT EXISTS email_status VARCHAR(30) DEFAULT 'pending',
      ADD COLUMN IF NOT EXISTS email_sent_at DATETIME NULL,
      ADD COLUMN IF NOT EXISTS email_error TEXT NULL;
    """
    )
    # Add index on email_status for faster filtering
    op.create_index('ix_nfcom_email_status', 'nfcom', ['email_status'])


def downgrade():
    # Drop index and columns
    try:
        op.drop_index('ix_nfcom_email_status', table_name='nfcom')
    except Exception:
        pass
    # Some MySQL versions don't support DROP COLUMN IF EXISTS in older syntax; do guarded drops
    op.execute("ALTER TABLE nfcom DROP COLUMN IF EXISTS email_error")
    op.execute("ALTER TABLE nfcom DROP COLUMN IF EXISTS email_sent_at")
    op.execute("ALTER TABLE nfcom DROP COLUMN IF EXISTS email_status")
