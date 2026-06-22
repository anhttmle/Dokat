"""create_posts_and_post_recipients

Revision ID: f1a2b3c4d5e6
Revises: e7d2a1f0c4b8
Create Date: 2026-06-22

Implements design §2.1 and §2.2 (F05):
- CREATE TABLE posts (expires_at + nullable latitude/longitude) with
  covering indexes on user_id and expires_at.
- CREATE TABLE post_recipients with UNIQUE (post_id, recipient_id) and
  covering indexes on post_id and recipient_id.
Refs: FR-5, FR-6; AC-F05-4; DL-F05-01, DL-F05-03, DL-F05-04;
F11 Design §2.3
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e7d2a1f0c4b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create posts and post_recipients tables with their indexes."""
    op.create_table(
        "posts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("s3_key", sa.Text(), nullable=False),
        sa.Column("cdn_url", sa.Text(), nullable=False),
        sa.Column(
            "expires_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column("latitude", sa.Numeric(11, 8), nullable=True),
        sa.Column("longitude", sa.Numeric(12, 8), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("idx_posts_user_id", "posts", ["user_id"])
    op.create_index("idx_posts_expires_at", "posts", ["expires_at"])

    op.create_table(
        "post_recipients",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "post_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("posts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "recipient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "seen_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "post_id",
            "recipient_id",
            name="post_recipients_unique_pair",
        ),
    )
    op.create_index(
        "idx_post_recipients_post",
        "post_recipients",
        ["post_id"],
    )
    op.create_index(
        "idx_post_recipients_recipient",
        "post_recipients",
        ["recipient_id"],
    )


def downgrade() -> None:
    """Drop post_recipients and posts tables and their indexes."""
    op.drop_index(
        "idx_post_recipients_recipient",
        table_name="post_recipients",
    )
    op.drop_index(
        "idx_post_recipients_post",
        table_name="post_recipients",
    )
    op.drop_table("post_recipients")

    op.drop_index("idx_posts_expires_at", table_name="posts")
    op.drop_index("idx_posts_user_id", table_name="posts")
    op.drop_table("posts")
