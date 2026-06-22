"""SQLAlchemy ORM models for users and user_providers tables."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class OAuthProvider(enum.StrEnum):
    """Supported OAuth providers."""

    apple = "apple"
    google = "google"
    facebook = "facebook"


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


class User(Base):
    """Represents a user (guest or linked)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    firebase_uid: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False
    )
    is_anonymous: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    display_name: Mapped[str | None] = mapped_column(String(100))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    fcm_token: Mapped[str | None] = mapped_column(Text)
    force_link_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    providers: Mapped[list["UserProvider"]] = relationship(
        "UserProvider", back_populates="user", cascade="all, delete-orphan"
    )


class UserProvider(Base):
    """OAuth provider linked to a user account."""

    __tablename__ = "user_providers"
    __table_args__ = (UniqueConstraint("provider", "provider_uid"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[OAuthProvider] = mapped_column(
        Enum(OAuthProvider, name="oauth_provider"), nullable=False
    )
    provider_uid: Mapped[str] = mapped_column(String(256), nullable=False)
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="providers")
