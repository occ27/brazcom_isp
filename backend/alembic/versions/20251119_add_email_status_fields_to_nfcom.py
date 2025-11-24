"""add email status fields to nfcom

Revision ID: 20251119_add_email_status_fields_to_nfcom
Revises: 20251119_add_nfcom_email_jobs_and_statuses
Create Date: 2025-11-19 00:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251119_add_email_status_fields_to_nfcom'
down_revision = '20251119_add_nfcom_email_jobs_and_statuses'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('nfcom', sa.Column('email_status', sa.String(30), nullable=False, server_default='pending'))
    op.add_column('nfcom', sa.Column('email_sent_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('nfcom', sa.Column('email_error', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('nfcom', 'email_error')
    op.drop_column('nfcom', 'email_sent_at')
    op.drop_column('nfcom', 'email_status')
