"""Unit tests for report_service — persist user reports.

Reports store a fixed-enum reason for the moderation team and never
auto-block or hide the reported user (AC-F10-5). Self-reports and
out-of-enum reasons are rejected (DL-F10-06, DL-F10-11).

Refs: Design §1.4, §6.2; FR-6, FR-7; AC-F10-5; DL-F10-06
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.block import BlockedUser
from app.models.report import Report, ReportReason
from app.models.user import Base, User
from app.services.report_service import (
    InvalidReasonError,
    SelfReportError,
    report_user,
)


@pytest.fixture()
def db_session() -> Session:
    """Isolated SQLite in-memory session per test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=True)
    session = factory()
    yield session
    session.close()
    engine.dispose()


def _make_user(db: Session, *, firebase_uid: str) -> User:
    """Insert and return a minimal User row."""
    now = datetime.now(UTC)
    user = User(
        firebase_uid=firebase_uid,
        is_anonymous=False,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_report_inserts_row(db_session: Session) -> None:
    """Reporting inserts a row with the chosen reason (AC-F10-5)."""
    a = _make_user(db_session, firebase_uid="a")
    b = _make_user(db_session, firebase_uid="b")

    report = report_user(
        db_session,
        reporter_id=str(a.id),
        reported_user_id=str(b.id),
        reason="spam",
    )

    stored = db_session.query(Report).filter(Report.id == report.id).first()
    assert stored is not None
    assert stored.reporter_id == a.id
    assert stored.reported_user_id == b.id
    assert stored.reason == ReportReason.spam


def test_report_invalid_reason(db_session: Session) -> None:
    """A reason outside the enum raises InvalidReasonError (DL-F10-06)."""
    a = _make_user(db_session, firebase_uid="a")
    b = _make_user(db_session, firebase_uid="b")

    with pytest.raises(InvalidReasonError):
        report_user(
            db_session,
            reporter_id=str(a.id),
            reported_user_id=str(b.id),
            reason="not-a-reason",
        )


def test_report_self_raises(db_session: Session) -> None:
    """Reporting oneself raises SelfReportError."""
    a = _make_user(db_session, firebase_uid="a")

    with pytest.raises(SelfReportError):
        report_user(
            db_session,
            reporter_id=str(a.id),
            reported_user_id=str(a.id),
            reason="spam",
        )


def test_report_does_not_block(db_session: Session) -> None:
    """Reporting never creates a blocked_users row (AC-F10-5)."""
    a = _make_user(db_session, firebase_uid="a")
    b = _make_user(db_session, firebase_uid="b")

    report_user(
        db_session,
        reporter_id=str(a.id),
        reported_user_id=str(b.id),
        reason="harassment",
    )

    assert db_session.query(BlockedUser).count() == 0
