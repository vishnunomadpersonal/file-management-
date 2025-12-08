"""Make appointment_id optional in files table

Revision ID: make_appt_optional
Revises: e1c120d12bbc
Create Date: 2025-12-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'make_appt_optional'
down_revision: Union[str, None] = 'add_user_status'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the foreign key constraint first
    op.drop_constraint('fk_files_appointment_id', 'files', type_='foreignkey')
    
    # Modify the column to be nullable
    op.alter_column('files', 'appointment_id',
                    existing_type=sa.VARCHAR(36),
                    nullable=True)
    
    # Re-add the foreign key constraint (now with nullable column)
    op.create_foreign_key('fk_files_appointment_id', 'files', 'appointments',
                          ['appointment_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    # Drop the foreign key constraint
    op.drop_constraint('fk_files_appointment_id', 'files', type_='foreignkey')
    
    # Make the column NOT NULL again (will fail if there are NULL values)
    op.alter_column('files', 'appointment_id',
                    existing_type=sa.VARCHAR(36),
                    nullable=False)
    
    # Re-add the foreign key constraint
    op.create_foreign_key('fk_files_appointment_id', 'files', 'appointments',
                          ['appointment_id'], ['id'])
