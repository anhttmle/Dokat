"""create_user_providers_table

Revision ID: c526c80e8e72
Revises: ab39c569791b
Create Date: 2026-06-19

Implements design §2.2: ENUM oauth_provider, bảng user_providers,
indexes idx_user_providers_user_id và idx_user_providers_lookup.
Refs: FR-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c526c80e8e72"
down_revision: Union[str, Sequence[str], None] = "ab39c569791b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OAUTH_PROVIDER = postgresql.ENUM(
    "apple",
    "google",
    "facebook",
    name="oauth_provider",
    create_type=False,
)


def upgrade() -> None:
    """Create oauth_provider ENUM, user_providers table, and indexes."""
    _OAUTH_PROVIDER.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "user_providers",
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
            "provider",
            postgresql.ENUM(
                "apple",
                "google",
                "facebook",
                name="oauth_provider",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("provider_uid", sa.String(256), nullable=False),
        sa.Column(
            "linked_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "provider",
            "provider_uid",
            name="uq_user_providers_provider_uid",
        ),
    )

    op.create_index(
        "idx_user_providers_user_id",
        "user_providers",
        ["user_id"],
    )
    op.create_index(
        "idx_user_providers_lookup",
        "user_providers",
        ["provider", "provider_uid"],
    )


def downgrade() -> None:
    """Drop indexes, user_providers table, and oauth_provider ENUM."""
    op.drop_index("idx_user_providers_lookup", table_name="user_providers")
    op.drop_index("idx_user_providers_user_id", table_name="user_providers")
    op.drop_table("user_providers")
    _OAUTH_PROVIDER.drop(op.get_bind(), checkfirst=True)
