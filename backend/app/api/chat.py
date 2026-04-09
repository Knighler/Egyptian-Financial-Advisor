import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user
from app.schemas.chat import ChatIn, ChatOut
from app.services.agent import QuotaExceededError, run_financial_agent
from app.services.firebase_admin import get_firestore_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatOut)
def chat(payload: ChatIn, user: dict[str, Any] = Depends(get_current_user)) -> ChatOut:
    uid = user.get("uid")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing uid",
        )

    db = get_firestore_client()
    profile_doc = db.collection("users").document(uid).get()

    if not profile_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User profile missing. Complete onboarding first.",
        )

    profile = profile_doc.to_dict() or {}

    try:
        answer = run_financial_agent(payload.message, profile)
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
