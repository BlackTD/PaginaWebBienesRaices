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
    op.add_column('users', sa.Column('gmail', sa.String(length=255), nullable=True))
    op.create_unique_constraint('uq_users_gmail', 'users', ['gmail'])


def downgrade():
    op.drop_constraint('uq_users_gmail', 'users', type_='unique')
    op.drop_column('users', 'gmail')
