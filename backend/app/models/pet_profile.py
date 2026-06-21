"""SQLAlchemy ORM model for the pet_profiles table."""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.user import Base


class PetSpecies(str, enum.Enum):
    """Supported pet species (MVP: dog and cat only)."""

    dog = "dog"
    cat = "cat"


class PetGender(str, enum.Enum):
    """Pet gender; ``unknown`` is the default when AI is not confident."""

    male = "male"
    female = "female"
    unknown = "unknown"


class PetProfile(Base):
    """Represents a pet profile owned by a user.

    Backend enforces a 1-pet-per-free-user limit at the service layer
    (Design 4.2); the schema itself allows multiple rows per user.
    ``native_enum=False`` keeps the species/gender enums portable across
    PostgreSQL and the SQLite engine used in the test suite (DL-F02-07).
    """

    __tablename__ = "pet_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    species: Mapped[PetSpecies] = mapped_column(
        Enum(PetSpecies, name="pet_species", native_enum=False),
        nullable=False,
    )
    gender: Mapped[PetGender] = mapped_column(
        Enum(PetGender, name="pet_gender", native_enum=False),
        nullable=False,
        default=PetGender.unknown,
    )
    birthdate: Mapped[date | None] = mapped_column(Date)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
