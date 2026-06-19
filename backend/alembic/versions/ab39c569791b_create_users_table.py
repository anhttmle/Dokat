"""create_users_table

Revision ID: ab39c569791b
Revises:
Create Date: 2026-06-19 09:37:21.462452

Implements design §2.1: bảng users với index idx_users_firebase_uid.
Refs: FR-1, FR-2
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "ab39c569791b"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the users table and idx_users_firebase_uid index."""
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "firebase_uid",
            sa.String(128),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "is_anonymous",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("TRUE"),
        ),
        sa.Column("display_name", sa.String(100), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column(
            "force_link_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "idx_users_firebase_uid",
        "users",
        ["firebase_uid"],
    )


def downgrade() -> None:
    """Drop idx_users_firebase_uid index and users table."""
    op.drop_index("idx_users_firebase_uid", table_name="users")
    op.drop_table("users")
