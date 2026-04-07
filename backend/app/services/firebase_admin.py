import json
from functools import lru_cache
from pathlib import Path

from firebase_admin import App, auth, credentials, firestore, get_app, initialize_app

from app.core.config import settings


def _load_credentials() -> credentials.Base:
    service_account = settings.firebase_service_account_json.strip()
    if not service_account:
        raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_JSON is not set")

    if service_account.startswith("{"):
        payload = json.loads(service_account)
        return credentials.Certificate(payload)

    key_path = Path(service_account).expanduser()
    if not key_path.is_absolute():
        key_path = Path.cwd() / key_path

    if not key_path.exists():
        raise RuntimeError(f"Firebase service account key not found: {key_path}")

    return credentials.Certificate(str(key_path))


@lru_cache(maxsize=1)
def get_firebase_app() -> App:
    try:
        return get_app()
    except ValueError:
        pass

    cert = _load_credentials()
    options = {}
    if settings.firebase_storage_bucket:
        options["storageBucket"] = settings.firebase_storage_bucket

    return initialize_app(cert, options=options)


def verify_user_token(id_token: str) -> dict:
    return auth.verify_id_token(id_token, app=get_firebase_app())


def get_firestore_client() -> firestore.Client:
    return firestore.client(
        app=get_firebase_app(), database_id=settings.firestore_database_id
    )
