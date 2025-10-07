"""drop files.celery_task_id foreign key

Revision ID: d3b2a1c4f789
Revises: e1c120d12bbc
Create Date: 2025-08-14 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

# revision identifiers, used by Alembic.
revision: str = 'd3b2a1c4f789'
down_revision: Union[str, None] = 'e1c120d12bbc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    fks = inspector.get_foreign_keys('files')
    for fk in fks:
        referred_table = fk.get('referred_table')
        constrained_columns = fk.get('constrained_columns') or []
        if referred_table == 'celery_tasks' and 'celery_task_id' in constrained_columns:
            constraint_name = fk.get('name')
            if constraint_name:
                op.drop_constraint(constraint_name, 'files', type_='foreignkey')
            break


def downgrade() -> None:
    # Recreate FK to celery_tasks.task_id
    op.create_foreign_key(None, 'files', 'celery_tasks', ['celery_task_id'], ['task_id'])


