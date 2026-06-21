"""create_friendships_and_fcm_token

Revision ID: e7d2a1f0c4b8
Revises: 3b8e1f2a6d90
Create Date: 2026-06-21

Implements design §2.1 and §2.2:
- ALTER TABLE users ADD COLUMN fcm_token TEXT (nullable).
- CREATE TABLE friendships with CHECK (user_id_a < user_id_b),
  UNIQUE (user_id_a, user_id_b), and two covering indexes.
Refs: FR-8
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e7d2a1f0c4b8"
down_revision: Union[str, Sequence[str], None] = "3b8e1f2a6d90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add fcm_token to users; create friendships table and indexes."""
    op.add_column("users", sa.Column("fcm_token", sa.Text(), nullable=True))

    op.create_table(
        "friendships",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id_a",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id_b",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "user_id_a < user_id_b",
            name="friendships_canonical_order",
        ),
        sa.UniqueConstraint(
            "user_id_a",
            "user_id_b",
            name="friendships_unique_pair",
        ),
    )

    op.create_index(
        "idx_friendships_a",
        "friendships",
        ["user_id_a"],
    )
    op.create_index(
        "idx_friendships_b",
        "friendships",
        ["user_id_b"],
    )


def downgrade() -> None:
    """Drop indexes, friendships table, and fcm_token column."""
    op.drop_index("idx_friendships_b", table_name="friendships")
    op.drop_index("idx_friendships_a", table_name="friendships")
    op.drop_table("friendships")
    op.drop_column("users", "fcm_token")
