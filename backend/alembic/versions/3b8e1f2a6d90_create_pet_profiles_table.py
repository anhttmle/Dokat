"""create_pet_profiles_table

Revision ID: 3b8e1f2a6d90
Revises: c526c80e8e72
Create Date: 2026-06-21

Implements design §2.2: ENUM pet_species, ENUM pet_gender, bảng
pet_profiles, và index idx_pet_profiles_user_id.
Refs: FR-3, FR-4
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "3b8e1f2a6d90"
down_revision: Union[str, Sequence[str], None] = "c526c80e8e72"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PET_SPECIES = postgresql.ENUM(
    "dog",
    "cat",
    name="pet_species",
    create_type=False,
)

_PET_GENDER = postgresql.ENUM(
    "male",
    "female",
    "unknown",
    name="pet_gender",
    create_type=False,
)


def upgrade() -> None:
    """Create pet_species/pet_gender ENUMs, pet_profiles table, index."""
    _PET_SPECIES.create(op.get_bind(), checkfirst=True)
    _PET_GENDER.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "pet_profiles",
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
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column(
            "species",
            postgresql.ENUM(
                "dog",
                "cat",
                name="pet_species",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "gender",
            postgresql.ENUM(
                "male",
                "female",
                "unknown",
                name="pet_gender",
                create_type=False,
            ),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column("birthdate", sa.Date(), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
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
        "idx_pet_profiles_user_id",
        "pet_profiles",
        ["user_id"],
    )


def downgrade() -> None:
    """Drop index, pet_profiles table, and ENUMs."""
    op.drop_index(
        "idx_pet_profiles_user_id", table_name="pet_profiles"
    )
    op.drop_table("pet_profiles")
    _PET_GENDER.drop(op.get_bind(), checkfirst=True)
    _PET_SPECIES.drop(op.get_bind(), checkfirst=True)
