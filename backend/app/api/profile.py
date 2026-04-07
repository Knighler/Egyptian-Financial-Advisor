from typing import Any

from firebase_admin import firestore
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user
from app.schemas.profile import ProfileIn
from app.services.firebase_admin import get_firestore_client

router = APIRouter(tags=["profile"])


@router.get("/profile/me")
def get_profile(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    uid = user.get("uid")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing uid",
        )

    db = get_firestore_client()
    snapshot = db.collection("users").document(uid).get()

    if not snapshot.exists:
        return {"has_profile": False, "profile": None}

    return {"has_profile": True, "profile": snapshot.to_dict()}


@router.post("/profile")
def upsert_profile(
    payload: ProfileIn, user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, str]:
    uid = user.get("uid")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing uid",
        )

    db = get_firestore_client()
    doc_ref = db.collection("users").document(uid)
    existing = doc_ref.get().exists

    profile_data = payload.model_dump()
    profile_data.update(
        {
            "uid": uid,
            "email": user.get("email", ""),
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
    )
    if not existing:
        profile_data["created_at"] = firestore.SERVER_TIMESTAMP

    doc_ref.set(profile_data, merge=True)

    return {"status": "saved", "uid": uid}
