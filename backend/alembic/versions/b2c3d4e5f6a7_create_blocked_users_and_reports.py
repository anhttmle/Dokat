"""create_blocked_users_and_reports

Revision ID: b2c3d4e5f6a7
Revises: f1a2b3c4d5e6
Create Date: 2026-06-22

Implements design §2.1 and §2.2 (F10):
- CREATE TABLE blocked_users with UNIQUE (blocker_id, blocked_id) and
  covering indexes on blocker_id and blocked_id.
- CREATE ENUM report_reason and TABLE reports with covering indexes on
  reporter_id and reported_user_id.
Refs: FR-4, FR-6, FR-7; DL-F10-03, DL-F10-04, DL-F10-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_REPORT_REASON = postgresql.ENUM(
    "spam",
    "inappropriate",
    "harassment",
    "other",
    name="report_reason",
    create_type=False,
)


def upgrade() -> None:
    """Create blocked_users, report_reason ENUM, reports, and indexes."""
    op.create_table(
        "blocked_users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "blocker_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "blocked_id",
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
        sa.UniqueConstraint(
            "blocker_id",
            "blocked_id",
            name="blocked_users_unique_pair",
        ),
    )
    op.create_index(
        "idx_blocked_users_blocker",
        "blocked_users",
        ["blocker_id"],
    )
    op.create_index(
        "idx_blocked_users_blocked",
        "blocked_users",
        ["blocked_id"],
    )

    _REPORT_REASON.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "reports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "reporter_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "reported_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "reason",
            postgresql.ENUM(
                "spam",
                "inappropriate",
                "harassment",
                "other",
                name="report_reason",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "idx_reports_reporter",
        "reports",
        ["reporter_id"],
    )
    op.create_index(
        "idx_reports_reported",
        "reports",
        ["reported_user_id"],
    )


def downgrade() -> None:
    """Drop reports, report_reason ENUM, blocked_users, and indexes."""
    op.drop_index("idx_reports_reported", table_name="reports")
    op.drop_index("idx_reports_reporter", table_name="reports")
    op.drop_table("reports")
    _REPORT_REASON.drop(op.get_bind(), checkfirst=True)

    op.drop_index("idx_blocked_users_blocked", table_name="blocked_users")
    op.drop_index("idx_blocked_users_blocker", table_name="blocked_users")
    op.drop_table("blocked_users")
