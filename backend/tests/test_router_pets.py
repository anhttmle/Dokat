"""Tests for the pets router (/pets).

Written TDD-style; tests are expected to FAIL until the pet service
endpoints are implemented in later F02 tasks.

Refs: Design 3.4-3.10, 6.1
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models.pet_profile import PetGender, PetProfile, PetSpecies
from app.models.photo import Photo  # noqa: F401 — registers table in Base
from app.models.user import Base, User
from app.routers.auth import get_db

_HEADERS = {"Authorization": "Bearer fake-token"}


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


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    """TestClient with the DB dependency overridden per test."""
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def _make_user(
    db_session: Session, *, firebase_uid: str = "pet-owner-uid"
) -> User:
    """Insert and return a user row."""
    now = datetime.now(timezone.utc)
    user = User(
        firebase_uid=firebase_uid,
        is_anonymous=False,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_pet(
    db_session: Session,
    user: User,
    *,
    name: str = "Mochi",
    species: PetSpecies = PetSpecies.dog,
    gender: PetGender = PetGender.male,
) -> PetProfile:
    """Insert and return a pet profile row owned by ``user``."""
    pet = PetProfile(
        user_id=user.id,
        name=name,
        species=species,
        gender=gender,
    )
    db_session.add(pet)
    db_session.commit()
    db_session.refresh(pet)
    return pet


def _make_photo(
    db_session: Session,
    user: User,
    *,
    pet: PetProfile | None = None,
    taken_at: datetime | None = None,
    cdn_url: str = "https://cdn.example.com/photos/test.jpg",
) -> Photo:
    """Insert and return a photo row owned by ``user``."""
    photo = Photo(
        user_id=user.id,
        pet_id=pet.id if pet is not None else None,
        cdn_url=cdn_url,
        taken_at=taken_at or datetime.now(timezone.utc),
    )
    db_session.add(photo)
    db_session.commit()
    db_session.refresh(photo)
    return photo


def test_create_pet_success_returns_201(
    client: TestClient, db_session: Session
) -> None:
    """Valid POST /pets inserts a row and returns 201 with non-null id."""
    _make_user(db_session)
    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = {"uid": "pet-owner-uid"}
        response = client.post(
            "/pets",
            headers=_HEADERS,
            json={
                "name": "Mochi",
                "species": "dog",
                "gender": "male",
                "birthdate": "2022-03-15",
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] is not None
    assert body["name"] == "Mochi"
    assert body["species"] == "dog"
    assert db_session.query(PetProfile).count() == 1


def test_create_pet_limit_reached_returns_403(  # noqa: E501
    client: TestClient, db_session: Session
) -> None:
    """A user with 1 pet gets 403 PET_LIMIT_REACHED on a 2nd create."""
    user = _make_user(db_session)
    _make_pet(db_session, user)
    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = {"uid": "pet-owner-uid"}
        response = client.post(
            "/pets",
            headers=_HEADERS,
            json={"name": "Second", "species": "cat"},
        )

    assert response.status_code == 403
    assert response.json()["error"] == "PET_LIMIT_REACHED"


def test_create_pet_defaults_gender_unknown(
    client: TestClient, db_session: Session
) -> None:
    """Omitting gender defaults to 'unknown'."""
    _make_user(db_session)
    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = {"uid": "pet-owner-uid"}
        response = client.post(
            "/pets",
            headers=_HEADERS,
            json={"name": "NoGender", "species": "cat"},
        )

    assert response.status_code == 201
    assert response.json()["gender"] == "unknown"


def test_create_pet_rejects_future_birthdate(
    client: TestClient, db_session: Session
) -> None:
    """A future birthdate is rejected with 422."""
    _make_user(db_session)
    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = {"uid": "pet-owner-uid"}
        response = client.post(
            "/pets",
            headers=_HEADERS,
            json={
                "name": "Future",
                "species": "dog",
                "birthdate": "2999-01-01",
            },
        )

    assert response.status_code == 422


def test_get_pets_returns_list(
    client: TestClient, db_session: Session
) -> None:
    """Seeding 1 pet then GET /pets returns exactly 1 element."""
    user = _make_user(db_session)
    _make_pet(db_session, user)
    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = {"uid": "pet-owner-uid"}
        response = client.get("/pets", headers=_HEADERS)

    assert response.status_code == 200
    assert len(response.json()["pets"]) == 1


def test_get_pets_empty_list(
    client: TestClient, db_session: Session
) -> None:
    """A user with no pets gets an empty list."""
    _make_user(db_session)
    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = {"uid": "pet-owner-uid"}
        response = client.get("/pets", headers=_HEADERS)

    assert response.status_code == 200
    assert response.json()["pets"] == []


def test_get_pet_not_owned_returns_404(  # noqa: E501
    client: TestClient, db_session: Session
) -> None:
    """Fetching another user's pet returns 404 PET_NOT_FOUND."""
    _make_user(db_session)
    other = _make_user(db_session, firebase_uid="other-uid")
    other_pet = _make_pet(db_session, other)
    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = {"uid": "pet-owner-uid"}
        response = client.get(
            f"/pets/{other_pet.id}", headers=_HEADERS
        )

    assert response.status_code == 404


def test_patch_pet_partial_update(
    client: TestClient, db_session: Session
) -> None:
    """Patching name leaves species and gender unchanged."""
    user = _make_user(db_session)
    pet = _make_pet(
        db_session, user, name="OldName", species=PetSpecies.dog
    )
    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = {"uid": "pet-owner-uid"}
        response = client.patch(
            f"/pets/{pet.id}",
            headers=_HEADERS,
            json={"name": "NewName"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "NewName"
    assert body["species"] == "dog"


def test_link_photo_success(
    client: TestClient, db_session: Session
) -> None:
    """Linking an unlinked photo returns 200 with link metadata.

    Refs: FR-10; Design §3.9; DL-F02-03, DL-F02-05
    """
    user = _make_user(db_session)
    pet = _make_pet(db_session, user)
    photo = _make_photo(db_session, user)
    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = {"uid": "pet-owner-uid"}
        response = client.patch(
            f"/pets/{pet.id}/link-photo",
            headers=_HEADERS,
            json={"photo_id": str(photo.id)},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["pet_id"] == str(pet.id)
    assert body["photo_id"] == str(photo.id)
    db_session.refresh(photo)
    assert photo.pet_id == pet.id


def test_link_photo_already_linked_returns_409(
    client: TestClient, db_session: Session
) -> None:
    """Linking a photo already tied to a pet returns 409.

    Refs: FR-10; Design §3.9; DL-F02-05
    """
    user = _make_user(db_session)
    pet = _make_pet(db_session, user)
    photo = _make_photo(db_session, user, pet=pet)
    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = {"uid": "pet-owner-uid"}
        response = client.patch(
            f"/pets/{pet.id}/link-photo",
            headers=_HEADERS,
            json={"photo_id": str(photo.id)},
        )

    assert response.status_code == 409
    assert response.json()["error"] == "PHOTO_ALREADY_LINKED"


def test_get_pet_photos_empty(
    client: TestClient, db_session: Session
) -> None:
    """A pet with no photos returns an empty timeline.

    Refs: Design §3.10; DL-F02-03
    """
    user = _make_user(db_session)
    pet = _make_pet(db_session, user)
    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = {"uid": "pet-owner-uid"}
        response = client.get(
            f"/pets/{pet.id}/photos", headers=_HEADERS
        )

    assert response.status_code == 200
    body = response.json()
    assert body["photos"] == []
    assert body["has_more"] is False


def test_get_pet_photos_ordered_by_taken_at_desc(
    client: TestClient, db_session: Session
) -> None:
    """3 photos with different taken_at are returned newest-first.

    Refs: Design §2.3, §3.10; DL-F02-03
    """
    now = datetime.now(timezone.utc)
    user = _make_user(db_session)
    pet = _make_pet(db_session, user)
    _make_photo(db_session, user, pet=pet, taken_at=now - timedelta(days=2))
    _make_photo(db_session, user, pet=pet, taken_at=now - timedelta(days=1))
    _make_photo(db_session, user, pet=pet, taken_at=now)

    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = {"uid": "pet-owner-uid"}
        response = client.get(
            f"/pets/{pet.id}/photos", headers=_HEADERS
        )

    assert response.status_code == 200
    photos = response.json()["photos"]
    assert len(photos) == 3
    taken_at = [p["taken_at"] for p in photos]
    assert taken_at == sorted(taken_at, reverse=True)


def test_get_pet_photos_pagination_returns_next_cursor(
    client: TestClient, db_session: Session
) -> None:
    """25 photos with limit=20 returns 20 items, has_more=True, next_cursor.

    Refs: Design §3.10; DL-F02-03
    """
    now = datetime.now(timezone.utc)
    user = _make_user(db_session)
    pet = _make_pet(db_session, user)
    for i in range(25):
        _make_photo(
            db_session,
            user,
            pet=pet,
            taken_at=now - timedelta(hours=i),
        )

    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = {"uid": "pet-owner-uid"}
        response = client.get(
            f"/pets/{pet.id}/photos?limit=20", headers=_HEADERS
        )

    assert response.status_code == 200
    body = response.json()
    assert len(body["photos"]) == 20
    assert body["has_more"] is True
    assert body["next_cursor"] is not None


def test_get_pet_photos_before_cursor_filters_correctly(
    client: TestClient, db_session: Session
) -> None:
    """Passing before=<cursor> returns only photos older than cursor.

    Refs: Design §3.10; DL-F02-03, DL-F02-05
    """
    now = datetime.now(timezone.utc)
    user = _make_user(db_session)
    pet = _make_pet(db_session, user)
    oldest = now - timedelta(days=2)
    middle = now - timedelta(days=1)
    newest = now
    _make_photo(db_session, user, pet=pet, taken_at=oldest)
    _make_photo(db_session, user, pet=pet, taken_at=middle)
    _make_photo(db_session, user, pet=pet, taken_at=newest)

    # Only photos older than `middle` should be returned.
    before_param = middle.isoformat()
    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = {"uid": "pet-owner-uid"}
        response = client.get(
            f"/pets/{pet.id}/photos?before={before_param}",
            headers=_HEADERS,
        )

    assert response.status_code == 200
    body = response.json()
    assert len(body["photos"]) == 1
    assert body["has_more"] is False


def test_get_pet_photos_not_owned_returns_404(
    client: TestClient, db_session: Session
) -> None:
    """GET /pets/{id}/photos for another user's pet returns 404.

    Refs: Design §3.10; DL-F02-05
    """
    _make_user(db_session)
    other = _make_user(db_session, firebase_uid="other-uid")
    other_pet = _make_pet(db_session, other)

    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = {"uid": "pet-owner-uid"}
        response = client.get(
            f"/pets/{other_pet.id}/photos", headers=_HEADERS
        )

    assert response.status_code == 404
