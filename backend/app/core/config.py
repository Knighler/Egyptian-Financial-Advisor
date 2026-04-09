import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv

logging.getLogger("dotenv.main").setLevel(logging.ERROR)
load_dotenv()


@dataclass(frozen=True)
class Settings:
    fastapi_env: str
    api_host: str
    api_port: int
    frontend_origin: str
    firebase_project_id: str
    firebase_storage_bucket: str
    firebase_service_account_json: str
    firestore_database_id: str
    google_cloud_project: str
    google_application_credentials: str
    bigquery_dataset: str
    bigquery_location: str
    google_genai_api_key: str
    google_genai_model: str


def get_settings() -> Settings:
    return Settings(
        fastapi_env=os.getenv("FASTAPI_ENV", "development"),
        api_host=os.getenv("API_HOST", "0.0.0.0"),
        api_port=int(os.getenv("API_PORT", "8000")),
        frontend_origin=os.getenv("FRONTEND_ORIGIN", "http://localhost:3000"),
        firebase_project_id=os.getenv("FIREBASE_PROJECT_ID", ""),
        firebase_storage_bucket=os.getenv("FIREBASE_STORAGE_BUCKET", ""),
        firebase_service_account_json=os.getenv(
            "FIREBASE_SERVICE_ACCOUNT_JSON", "./firebase-admin-key.json"
        ),
        firestore_database_id=os.getenv("FIRESTORE_DATABASE_ID", "efa-users"),
        google_cloud_project=os.getenv("GOOGLE_CLOUD_PROJECT", ""),
        google_application_credentials=os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""),
        bigquery_dataset=os.getenv("BIGQUERY_DATASET", "efa_main"),
        bigquery_location=os.getenv("BIGQUERY_LOCATION", "US"),
        google_genai_api_key=os.getenv("GOOGLE_GENAI_API_KEY", ""),
        google_genai_model=os.getenv("GOOGLE_GENAI_MODEL", "gemini-flash-latest"),
    )


settings = get_settings()
