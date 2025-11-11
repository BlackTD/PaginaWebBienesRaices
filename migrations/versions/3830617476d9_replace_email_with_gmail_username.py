"""replace email with gmail username

Revision ID: 3830617476d9
Revises: 20240604_add_gmail
Create Date: 2025-11-11 17:05:59.998464

"""
from __future__ import annotations

import re

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3830617476d9'
down_revision = '20240604_add_gmail'
branch_labels = None
depends_on = None


def _sanitize_username(source: str, fallback: str) -> str:
    base = re.sub(r'[^a-z0-9._-]', '', source.lower())
    return base or fallback


def upgrade():
    connection = op.get_bind()
    users = sa.table(
        'users',
        sa.column('id', sa.Integer()),
        sa.column('email', sa.String(length=255)),
        sa.column('gmail', sa.String(length=255)),
        sa.column('username', sa.String(length=150)),
    )

    with op.batch_alter_table('users', recreate='always') as batch_op:
        batch_op.add_column(sa.Column('username', sa.String(length=150), nullable=True))

    # Normalize gmail values and generate usernames
    existing_usernames: set[str] = set()
    rows = connection.execute(sa.select(users.c.id, users.c.email, users.c.gmail)).fetchall()
    for row in rows:
        email_value = (row.email or '').strip().lower()
        gmail_value = (row.gmail or '').strip().lower()
        normalized_gmail = gmail_value or email_value
        if not normalized_gmail:
            normalized_gmail = f'user{row.id}@gmail.com'

        base_username = _sanitize_username(
            normalized_gmail.split('@', 1)[0], f'user{row.id}'
        )
        candidate = base_username
        suffix = 1
        while candidate in existing_usernames:
            candidate = f'{base_username}{suffix}'
            suffix += 1
        existing_usernames.add(candidate)

        connection.execute(
            users.update()
            .where(users.c.id == row.id)
            .values(gmail=normalized_gmail, username=candidate)
        )

    with op.batch_alter_table('users', recreate='always') as batch_op:
        batch_op.drop_constraint('uq_users_gmail', type_='unique')
        batch_op.alter_column('gmail', existing_type=sa.String(length=255), nullable=False)
        batch_op.alter_column('username', existing_type=sa.String(length=150), nullable=False)
        batch_op.create_unique_constraint('uq_users_gmail', ['gmail'])
        batch_op.create_unique_constraint('uq_users_username', ['username'])
        batch_op.drop_column('email_confirmed')
        batch_op.drop_column('email')


def downgrade():
    connection = op.get_bind()
    users = sa.table(
        'users',
        sa.column('id', sa.Integer()),
        sa.column('email', sa.String(length=255)),
        sa.column('gmail', sa.String(length=255)),
        sa.column('username', sa.String(length=150)),
        sa.column('email_confirmed', sa.Boolean()),
    )

    with op.batch_alter_table('users', recreate='always') as batch_op:
        batch_op.add_column(sa.Column('email', sa.String(length=255), nullable=True))
        batch_op.add_column(
            sa.Column('email_confirmed', sa.Boolean(), server_default=sa.text('0'), nullable=False)
        )

    rows = connection.execute(sa.select(users.c.id, users.c.gmail)).fetchall()
    for row in rows:
        gmail_value = (row.gmail or '').strip().lower()
        connection.execute(
            users.update()
            .where(users.c.id == row.id)
            .values(email=gmail_value or None)
        )

    with op.batch_alter_table('users', recreate='always') as batch_op:
        batch_op.drop_constraint('uq_users_username', type_='unique')
        batch_op.drop_constraint('uq_users_gmail', type_='unique')
        batch_op.alter_column('email', existing_type=sa.String(length=255), nullable=False)
        batch_op.alter_column('gmail', existing_type=sa.String(length=255), nullable=True)
        batch_op.drop_column('username')
        batch_op.create_unique_constraint('uq_users_gmail', ['gmail'])
