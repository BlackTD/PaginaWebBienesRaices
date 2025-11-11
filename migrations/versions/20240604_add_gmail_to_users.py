"""Add Gmail field to users

Revision ID: 20240604_add_gmail
Revises: 5638244539d7
Create Date: 2024-06-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20240604_add_gmail'
down_revision = '5638244539d7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', recreate='always') as batch_op:
        batch_op.add_column(sa.Column('gmail', sa.String(length=255), nullable=True))
        batch_op.create_unique_constraint('uq_users_gmail', ['gmail'])


def downgrade():
    with op.batch_alter_table('users', recreate='always') as batch_op:
        batch_op.drop_constraint('uq_users_gmail', type_='unique')
        batch_op.drop_column('gmail')
