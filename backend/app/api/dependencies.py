from typing import Any

from fastapi import Depends, Header, HTTPException, status

from app.services.firebase_admin import verify_user_token


def get_bearer_token(authorization: str = Header(default="")) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    return authorization.replace("Bearer ", "", 1).strip()


def get_current_user(token: str = Depends(get_bearer_token)) -> dict[str, Any]:
    try:
        return verify_user_token(token)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Firebase token",
        ) from exc
