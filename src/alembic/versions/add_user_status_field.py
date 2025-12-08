"""add user status field

Revision ID: add_user_status
Revises: de84cb899fc5
Create Date: 2024-12-07

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_user_status'
down_revision = 'feedback_persistence'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add status column to users table
    op.add_column('users', sa.Column('status', sa.String(50), nullable=True, server_default='approved'))
    
    # Update existing users to have 'approved' status
    op.execute("UPDATE users SET status = 'approved' WHERE status IS NULL")


def downgrade() -> None:
    op.drop_column('users', 'status')
