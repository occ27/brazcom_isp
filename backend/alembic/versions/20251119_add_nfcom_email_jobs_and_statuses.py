"""add nfcom email jobs and statuses

Revision ID: 20251119_add_nfcom_email_jobs_and_statuses
Revises: 
Create Date: 2025-11-19 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251119_add_nfcom_email_jobs_and_statuses'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'nfcom_email_jobs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('empresa_id', sa.Integer(), nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('processed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failures', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(30), nullable=False, server_default='pending')
    )

    op.create_table(
        'nfcom_email_statuses',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('nfcom_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_table('nfcom_email_statuses')
    op.drop_table('nfcom_email_jobs')
