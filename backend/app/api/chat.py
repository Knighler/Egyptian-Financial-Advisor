import logging
from typing import Any

from firebase_admin import firestore
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user
from app.schemas.chat import ChatIn, ChatOut
from app.services.agent import (
    QuotaExceededError,
    extract_conversation_updates,
    run_financial_agent,
)
from app.services.firebase_admin import get_firestore_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

PROFILE_FIELDS = (
    "monthly_income",
    "savings",
    "investment_goal",
    "risk_tolerance",
)


def _extract_profile(document_data: dict[str, Any]) -> dict[str, Any]:
    nested_profile = document_data.get("profile")
    profile = nested_profile if isinstance(nested_profile, dict) else {}

    merged_profile: dict[str, Any] = {}
    for field in PROFILE_FIELDS:
        if field in profile:
            merged_profile[field] = profile[field]
        elif field in document_data:
            merged_profile[field] = document_data[field]

    return merged_profile


@router.post("/chat", response_model=ChatOut)
def chat(payload: ChatIn, user: dict[str, Any] = Depends(get_current_user)) -> ChatOut:
    uid = user.get("uid")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing uid",
        )

    db = get_firestore_client()
    user_doc_ref = db.collection("users").document(uid)
    profile_doc = user_doc_ref.get()

    if not profile_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User profile missing. Complete onboarding first.",
        )

    user_document = profile_doc.to_dict() or {}
    profile = _extract_profile(user_document)
    existing_memory = user_document.get("memory")
    if not isinstance(existing_memory, dict):
        existing_memory = {}

    try:
        answer = run_financial_agent(payload.message, profile)

        try:
            updates = extract_conversation_updates(
                user_message=payload.message,
                assistant_response=answer,
                profile=profile,
                existing_memory=existing_memory,
            )

            profile_updates = updates.get("profile_updates", {})
            memory_updates = updates.get("memory", {})

            merged_profile = dict(profile)
            if isinstance(profile_updates, dict):
                merged_profile.update(profile_updates)

            merged_memory = dict(existing_memory)
            if isinstance(memory_updates, dict):
                merged_memory.update(memory_updates)
            merged_memory["last_interaction"] = firestore.SERVER_TIMESTAMP

            firestore_update: dict[str, Any] = {
                "updated_at": firestore.SERVER_TIMESTAMP,
                "profile": merged_profile,
                "memory": merged_memory,
            }

            # Keep legacy flattened profile fields for compatibility with existing frontend code.
            firestore_update.update(merged_profile)
            user_doc_ref.set(firestore_update, merge=True)
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "Failed to persist conversation memory/profile updates",
                extra={"uid": uid},
                exc_info=exc,
            )

        return ChatOut(response=answer)
    except QuotaExceededError as exc:
        logger.warning("Chat quota exceeded", extra={"uid": uid})
        headers = (
            {"Retry-After": str(exc.retry_after_seconds)}
            if exc.retry_after_seconds
            else None
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "AI quota is currently exhausted for this project. "
                "Please try again later or enable billing/increase Gemini quota."
            ),
            headers=headers,
        ) from exc
    except RuntimeError as exc:
        logger.warning("Chat runtime failure", extra={"uid": uid})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The advisory engine is temporarily unavailable. "
                "Please try again in a moment."
            ),
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Chat engine failure")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The advisory engine is temporarily unavailable. "
                "Please try again in a moment."
            ),
        ) from exc
