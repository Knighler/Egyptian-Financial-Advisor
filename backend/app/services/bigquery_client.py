import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from google.api_core.exceptions import NotFound
from google.cloud import bigquery

from app.core.config import settings

logger = logging.getLogger(__name__)


def _ensure_google_credentials() -> None:
    credentials_path = settings.google_application_credentials.strip()
    if not credentials_path:
        return

    resolved = Path(credentials_path).expanduser()
    if not resolved.is_absolute():
        resolved = Path.cwd() / resolved

    if not resolved.exists():
        raise RuntimeError(f"GOOGLE_APPLICATION_CREDENTIALS path not found: {resolved}")

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(resolved)


@lru_cache(maxsize=1)
def get_bigquery_client() -> bigquery.Client:
    _ensure_google_credentials()

    return bigquery.Client(
        project=settings.google_cloud_project or None,
        location=settings.bigquery_location or None,
    )


def run_select_query(
    sql: str, parameters: list[bigquery.ScalarQueryParameter] | None = None
) -> list[dict[str, Any]]:
    if not sql.lstrip().upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed")

    query_config = bigquery.QueryJobConfig(query_parameters=parameters or [])
    logger.info("BigQuery SQL: %s | params=%s", sql, parameters or [])

    client = get_bigquery_client()
    configured_location = (settings.bigquery_location or "").strip() or None
    candidate_locations: list[str | None] = []
    for location in (configured_location, "US", "EU", None):
        if location not in candidate_locations:
            candidate_locations.append(location)

    last_error: Exception | None = None
    for location in candidate_locations:
        try:
            rows = client.query(sql, job_config=query_config, location=location).result()
            if location != configured_location:
                logger.warning(
                    "BigQuery location fallback in use. configured=%s active=%s",
                    configured_location,
                    location,
                )
            return [dict(row.items()) for row in rows]
        except NotFound as exc:
            last_error = exc
            message = str(exc).lower()
            if "was not found in location" in message:
                logger.warning(
                    "BigQuery dataset not found in location '%s'. Trying next location.",
                    location,
                )
                continue
            raise

    if last_error:
        raise RuntimeError(
            "BigQuery dataset location mismatch. "
            "Update BIGQUERY_LOCATION to your dataset region (for example US or EU)."
        ) from last_error

    raise RuntimeError("BigQuery query failed for an unknown reason.")
