"""add supabase_uid to users table

Revision ID: 7a4b42a546b5
Revises: 2cd2572afe9d
Create Date: 2026-03-30 13:13:19.743148

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a4b42a546b5'
down_revision: Union[str, Sequence[str], None] = '2cd2572afe9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('supabase_uid', sa.String(), nullable=True))
        batch_op.create_unique_constraint('uq_users_supabase_uid', ['supabase_uid'])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_constraint('uq_users_supabase_uid', type_='unique')
        batch_op.drop_column('supabase_uid')
