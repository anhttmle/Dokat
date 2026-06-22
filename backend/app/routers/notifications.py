"""Notification preferences router (F09).

Endpoints (prefix ``/notifications``):
  GET  /notifications/preferences              — list all 4 prefs
  PUT  /notifications/preferences/{type}       — upsert single pref

Refs: Design §3.2, §3.3; AC-F09-4, AC-F09-5
"""

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.models.notification_pref import ReminderType
from app.models.user import User
from app.routers.auth import get_db
from app.schemas.notification import PreferencesResponse, SetPreferenceRequest
from app.services import notification_pref_service

router = APIRouter(
    prefix="/notifications", tags=["notifications"]
)


def _get_user_id(request: Request, db: Session) -> uuid.UUID:
    """Resolve Firebase UID → internal UUID."""
    firebase_uid: str = request.state.firebase_uid
    user = (
        db.query(User)
        .filter(User.firebase_uid == firebase_uid)
        .first()
    )
    if user is None:
        raise LookupError(f"User not found: {firebase_uid}")
    return user.id


@router.get("/preferences", response_model=PreferencesResponse)
def get_preferences(
    request: Request,
    db: Session = Depends(get_db),
) -> PreferencesResponse:
    """Return all four reminder preferences for the current user.

    Missing rows default to ``true`` (opt-out model, AC-F09-4).
    """
    user_id = _get_user_id(request, db)
    prefs = notification_pref_service.get_preferences(db, user_id)
    return PreferencesResponse.from_dict(prefs)


@router.put(
    "/preferences/{reminder_type}",
    status_code=204,
)
def set_preference(
    reminder_type: ReminderType,
    payload: SetPreferenceRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Upsert a single reminder preference (idempotent, returns 204)."""
    user_id = _get_user_id(request, db)
    notification_pref_service.set_preference(
        db, user_id, reminder_type, payload.enabled
    )
    return JSONResponse(status_code=204, content=None)
