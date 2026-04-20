import json
import logging
from functools import lru_cache
from typing import Any

from google import genai
from google.genai import types
from langchain_core.tools import tool

from app.core.config import settings

logger = logging.getLogger(__name__)

SEARCH_MODEL_FALLBACKS = (
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-2.0-flash",
)


def _to_json_payload(payload: Any) -> str:
    return json.dumps(payload, default=str)


@lru_cache(maxsize=1)
def _get_genai_client() -> genai.Client:
    if not settings.google_genai_api_key:
        raise RuntimeError("GOOGLE_GENAI_API_KEY is not configured")
    return genai.Client(api_key=settings.google_genai_api_key)


def _candidate_models() -> list[str]:
    configured = (settings.google_genai_model or "").strip()
    candidates: list[str] = []

    for model_name in (configured, *SEARCH_MODEL_FALLBACKS):
        if model_name and model_name not in candidates:
            candidates.append(model_name)

    return candidates


def _extract_sources(response: Any) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    seen: set[str] = set()

    for candidate in getattr(response, "candidates", []) or []:
        grounding_metadata = getattr(candidate, "grounding_metadata", None)
        if not grounding_metadata:
            continue

        for chunk in getattr(grounding_metadata, "grounding_chunks", []) or []:
            web = getattr(chunk, "web", None)
            if not web:
                continue

            uri = (getattr(web, "uri", "") or "").strip()
            if not uri or uri in seen:
                continue

            seen.add(uri)
            sources.append(
                {
                    "title": (getattr(web, "title", "") or "").strip() or uri,
                    "uri": uri,
                }
            )

    return sources


def _extract_web_search_queries(response: Any) -> list[str]:
    queries: list[str] = []
    seen: set[str] = set()

    for candidate in getattr(response, "candidates", []) or []:
        grounding_metadata = getattr(candidate, "grounding_metadata", None)
        if not grounding_metadata:
            continue

        for query in getattr(grounding_metadata, "web_search_queries", []) or []:
            normalized = str(query).strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                queries.append(normalized)

    return queries


def _is_model_not_found_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "not_found" in message or "is not found" in message


@tool
def search_web_with_gemini(query: str) -> str:
    """Use Gemini native Google Search grounding for latest news, live prices, or topics not covered in the database."""
    cleaned_query = query.strip()
    if not cleaned_query:
        return _to_json_payload(
            {
                "status": "invalid_request",
                "message": "A search query is required.",
            }
        )

    last_error: Exception | None = None
    client = _get_genai_client()

    for model_name in _candidate_models():
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=cleaned_query,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                ),
            )

            return _to_json_payload(
                {
                    "status": "ok",
                    "provider": "gemini_google_search",
                    "model": model_name,
                    "query": cleaned_query,
                    "answer": (getattr(response, "text", "") or "").strip(),
                    "sources": _extract_sources(response),
                    "web_search_queries": _extract_web_search_queries(response),
                }
            )
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if _is_model_not_found_error(exc):
                logger.warning("Gemini search model unavailable: %s", model_name)
                continue
            break

    return _to_json_payload(
        {
            "status": "error",
            "provider": "gemini_google_search",
            "query": cleaned_query,
            "message": "Gemini web search failed.",
            "error": str(last_error) if last_error else "Unknown error",
        }
    )
