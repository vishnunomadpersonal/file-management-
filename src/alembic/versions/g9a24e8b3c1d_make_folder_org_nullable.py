"""Make folder organization_id nullable

Revision ID: g9a24e8b3c1d
Revises: f8d23e9a1b2c
Create Date: 2024-01-21 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g9a24e8b3c1d'
down_revision: Union[str, None] = 'f8d23e9a1b2c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the existing unique index that includes organization_id
    op.drop_index('ix_folders_org_path', table_name='folders')
    
    # Modify organization_id column to be nullable
    op.alter_column(
        'folders',
        'organization_id',
        existing_type=sa.VARCHAR(36),
        nullable=True
    )
    
    # Recreate the index with path prefix
    op.create_index('ix_folders_org_path', 'folders', ['organization_id', sa.text('path(191)')], unique=False)


def downgrade() -> None:
    # Drop the index
    op.drop_index('ix_folders_org_path', table_name='folders')
    
    # Make organization_id NOT NULL again
    op.alter_column(
        'folders',
        'organization_id',
        existing_type=sa.VARCHAR(36),
        nullable=False
    )
    
    # Recreate the unique index
    op.create_index('ix_folders_org_path', 'folders', ['organization_id', sa.text('path(191)')], unique=True)
