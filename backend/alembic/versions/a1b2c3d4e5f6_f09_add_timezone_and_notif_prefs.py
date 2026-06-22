"""f09_add_timezone_and_notif_prefs

Revision ID: a1b2c3d4e5f6
Revises: b2c3d4e5f6a7
Create Date: 2026-06-22

Implements F09 schema changes (Design §2.1, §2.2):
- ALTER TABLE users ADD COLUMN timezone TEXT (nullable).
- CREATE TABLE notification_preferences with UNIQUE (user_id,
  reminder_type) and index idx_notif_pref_user (user_id).

Refs: Design §2.1, §2.2; DL-F09-02, DL-F09-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add timezone to users; create notification_preferences table."""
    op.add_column("users", sa.Column("timezone", sa.Text(), nullable=True))

    op.create_table(
        "notification_preferences",
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
        sa.Column(
            "reminder_type",
            sa.VARCHAR(length=20),
            nullable=False,
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "user_id",
            "reminder_type",
            name="notif_pref_unique_pair",
        ),
    )
    op.create_index(
        "idx_notif_pref_user",
        "notification_preferences",
        ["user_id"],
    )


def downgrade() -> None:
    """Drop notification_preferences table and timezone column."""
    op.drop_index(
        "idx_notif_pref_user",
        table_name="notification_preferences",
    )
    op.drop_table("notification_preferences")
    op.drop_column("users", "timezone")
