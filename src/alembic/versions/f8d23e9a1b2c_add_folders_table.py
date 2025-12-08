"""Add folders table and folder_id to files

Revision ID: f8d23e9a1b2c
Revises: make_appt_optional
Create Date: 2024-01-20 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8d23e9a1b2c'
down_revision: Union[str, None] = 'make_appt_optional'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create folders table
    op.create_table(
        'folders',
        sa.Column('id', sa.VARCHAR(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('parent_id', sa.VARCHAR(36), sa.ForeignKey('folders.id', ondelete='CASCADE'), nullable=True),
        sa.Column('organization_id', sa.VARCHAR(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('created_by', sa.VARCHAR(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('path', sa.VARCHAR(500), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create index for path lookups (with prefix for MySQL)
    op.create_index('ix_folders_org_path', 'folders', ['organization_id', sa.text('path(191)')], unique=True)
    
    # Create unique constraint for folder name within same parent
    op.create_index('ix_folders_parent_name', 'folders', ['organization_id', 'parent_id', 'name'], unique=False)
    
    # Add organization_id and folder_id columns to files table
    op.add_column('files', sa.Column('organization_id', sa.VARCHAR(36), nullable=True))
    op.add_column('files', sa.Column('folder_id', sa.VARCHAR(36), nullable=True))
    
    # Add foreign keys for the new columns
    op.create_foreign_key(
        'fk_files_organization_id',
        'files', 'organizations',
        ['organization_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_files_folder_id',
        'files', 'folders',
        ['folder_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Create index for files by organization and folder
    op.create_index('ix_files_org_folder', 'files', ['organization_id', 'folder_id'])


def downgrade() -> None:
    # Drop indexes and foreign keys from files
    op.drop_index('ix_files_org_folder', table_name='files')
    op.drop_constraint('fk_files_folder_id', 'files', type_='foreignkey')
    op.drop_constraint('fk_files_organization_id', 'files', type_='foreignkey')
    
    # Drop columns from files
    op.drop_column('files', 'folder_id')
    op.drop_column('files', 'organization_id')
    
    # Drop folders table indexes
    op.drop_index('ix_folders_parent_name', table_name='folders')
    op.drop_index('ix_folders_org_path', table_name='folders')
    
    # Drop folders table
    op.drop_table('folders')
