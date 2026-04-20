import json
import logging
import math
import re
from functools import lru_cache
from typing import Any

from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError

from app.core.config import settings
from app.tools.market_tools import (
    get_available_database_topics,
    get_daily_pulse,
    get_historical_stats,
    get_ticker_performance,
    query_financial_database,
)
from app.tools.web_tools import search_web_with_gemini

logger = logging.getLogger(__name__)

LEGACY_MODEL_ALIASES = {
    "gemini-1.5-flash": "gemini-1.5-flash-latest",
    "gemini-1.5-pro": "gemini-1.5-pro-latest",
    "gemini-2.0-flash": "gemini-flash-latest",
    "gemini-2.0-flash-lite": "gemini-flash-lite-latest",
    "gemini-2.0-flash-lite-001": "gemini-flash-lite-latest",
}

FALLBACK_MODELS = (
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-flash-lite-latest",
    "gemini-2.5-flash-lite",
)


class QuotaExceededError(RuntimeError):
    def __init__(self, message: str, retry_after_seconds: int | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


PROFILE_NUMERIC_FIELDS = {"monthly_income", "savings"}
PROFILE_TEXT_FIELDS = {"investment_goal"}
PROFILE_INT_FIELDS = {"risk_tolerance"}


def _profile_to_context(profile: dict[str, Any]) -> str:
    allowed = {
        "monthly_income": profile.get("monthly_income"),
        "savings": profile.get("savings"),
        "investment_goal": profile.get("investment_goal"),
        "risk_tolerance": profile.get("risk_tolerance"),
    }
    return json.dumps(allowed, default=str)


def _normalize_model_content(content: Any) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        chunks: list[str] = []
        for part in content:
            if isinstance(part, str):
                chunks.append(part)
                continue
            if isinstance(part, dict) and "text" in part:
                chunks.append(str(part["text"]))
        return "\n".join(chunk for chunk in chunks if chunk).strip()

    return str(content)


def _parse_json_object(text: str) -> dict[str, Any] | None:
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw, flags=re.IGNORECASE).strip()
        raw = re.sub(r"```$", "", raw).strip()

    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    candidate = raw[start : end + 1]
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _to_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "")
        if cleaned:
            try:
                return float(cleaned)
            except ValueError:
                return None
    return None


def _sanitize_profile_updates(profile_updates: Any) -> dict[str, Any]:
    if not isinstance(profile_updates, dict):
        return {}

    cleaned: dict[str, Any] = {}

    for field in PROFILE_NUMERIC_FIELDS:
        if field not in profile_updates:
            continue
        value = _to_float(profile_updates.get(field))
        if value is None:
            continue
        if field == "monthly_income" and value <= 0:
            continue
        if field == "savings" and value < 0:
            continue
        cleaned[field] = value

    for field in PROFILE_TEXT_FIELDS:
        if field not in profile_updates:
            continue
        value = profile_updates.get(field)
        if not isinstance(value, str):
            continue
        normalized = " ".join(value.split())
        if 2 <= len(normalized) <= 200:
            cleaned[field] = normalized

    for field in PROFILE_INT_FIELDS:
        if field not in profile_updates:
            continue
        value = profile_updates.get(field)
        if isinstance(value, bool):
            continue
        if isinstance(value, float) and not value.is_integer():
            continue
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        if 1 <= parsed <= 10:
            cleaned[field] = parsed

    return cleaned


def _sanitize_memory(memory: Any) -> dict[str, Any]:
    if not isinstance(memory, dict):
        return {}

    cleaned: dict[str, Any] = {}

    summary = memory.get("last_summary")
    if isinstance(summary, str):
        normalized_summary = " ".join(summary.split())
        if normalized_summary:
            cleaned["last_summary"] = normalized_summary[:600]

    intentions = memory.get("key_intentions")
    if isinstance(intentions, list):
        unique_intentions: list[str] = []
        seen: set[str] = set()
        for item in intentions:
            if not isinstance(item, str):
                continue
            normalized_item = " ".join(item.split())
            lowered = normalized_item.lower()
            if not normalized_item or lowered in seen:
                continue
            seen.add(lowered)
            unique_intentions.append(normalized_item[:160])
            if len(unique_intentions) >= 6:
                break
        if unique_intentions:
            cleaned["key_intentions"] = unique_intentions

    return cleaned


def _extract_income_from_message(message: str) -> float | None:
    patterns = (
        r"(?:monthly\s+income|salary|earn(?:ing)?s?|make)\D{0,20}([0-9][0-9,]*(?:\.[0-9]+)?)",
        r"(?:now|currently)\D{0,20}([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:egp|le|l\.e\.)?\s*(?:monthly|per\s*month)?",
    )

    lowered = message.lower()
    for pattern in patterns:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if not match:
            continue
        value = _to_float(match.group(1))
        if value is not None and value > 0:
            return value
    return None


def _fallback_memory_summary(message: str) -> str:
    compact = " ".join(message.split())
    if not compact:
        return "User sent an empty message."
    if len(compact) <= 220:
        return f"User asked about: {compact}"
    return f"User asked about: {compact[:217].rstrip()}..."


def _extract_intentions_from_message(message: str) -> list[str]:
    compact = " ".join(message.split())
    if not compact:
        return []

    patterns = (
        r"(?:i\s+want\s+to|i\s+plan\s+to|my\s+goal\s+is\s+to)\s+([^\.!?]+)",
        r"(?:i\s+am\s+interested\s+in|interested\s+in)\s+([^\.!?]+)",
    )

    intentions: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, compact, flags=re.IGNORECASE):
            snippet = " ".join(match.group(1).split())
            if snippet and snippet not in intentions:
                intentions.append(snippet[:160])
            if len(intentions) >= 3:
                return intentions
    return intentions


@lru_cache(maxsize=1)
def get_chat_model(model_name: str) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=settings.google_genai_api_key,
        temperature=0.2,
        max_retries=1,
    )


def _candidate_models() -> list[str]:
    configured = (settings.google_genai_model or "").strip() or "gemini-flash-latest"
    candidates = [configured]

    alias = LEGACY_MODEL_ALIASES.get(configured)
    if alias and alias not in candidates:
        candidates.append(alias)

    for fallback in FALLBACK_MODELS:
        if fallback not in candidates:
            candidates.append(fallback)

    return candidates


def _is_model_not_found_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "not_found" in message or "is not found" in message


def _is_quota_exceeded_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "resource_exhausted" in message or "quota exceeded" in message


def _extract_retry_after_seconds(exc: Exception) -> int | None:
    message = str(exc)
    patterns = (
        r"retry in\s+([0-9]+(?:\.[0-9]+)?)s",
        r"retrydelay['\"]?\s*[:=]\s*['\"]?([0-9]+(?:\.[0-9]+)?)s",
    )
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if not match:
            continue
        try:
            return max(1, math.ceil(float(match.group(1))))
        except ValueError:
            continue
    return None


def _invoke_agent_with_model(
    model_name: str, message: str, system_prompt: str
) -> dict[str, Any]:
    agent = create_agent(
        model=get_chat_model(model_name),
        tools=[
            query_financial_database,
            get_available_database_topics,
            get_ticker_performance,
            get_daily_pulse,
            get_historical_stats,
            search_web_with_gemini,
        ],
        system_prompt=system_prompt,
    )

    return agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": message,
                }
            ]
        }
    )


def _extract_final_text(agent_result: dict[str, Any]) -> str:
    messages = agent_result.get("messages", [])
    if not messages:
        return "I could not generate a response right now."

    last_message = messages[-1]
    content = getattr(last_message, "content", "")
    return _normalize_model_content(content)


def _extract_memory_with_model(
    model_name: str,
    user_message: str,
    assistant_response: str,
    profile: dict[str, Any],
    existing_memory: dict[str, Any],
) -> dict[str, Any] | None:
    prompt = (
        "Extract structured user memory updates from the latest conversation turn.\n"
        "Return ONLY valid JSON with this exact shape:\n"
        "{\n"
        '  "profile_updates": {\n'
        '    "monthly_income": number (optional),\n'
        '    "savings": number (optional),\n'
        '    "investment_goal": string (optional),\n'
        '    "risk_tolerance": integer 1-10 (optional)\n'
        "  },\n"
        '  "memory": {\n'
        '    "last_summary": string,\n'
        '    "key_intentions": string[]\n'
        "  }\n"
        "}\n\n"
        "Rules:\n"
        "- Only include profile_updates fields when the user explicitly stated a change or a clear personal fact.\n"
        "- Do not infer numbers that were not explicitly provided by the user.\n"
        "- Keep last_summary concise (1 sentence) and include notable worries/interests if present.\n"
        "- key_intentions should be short actionable intentions from the user's words.\n"
        "- If nothing was updated, use an empty object for profile_updates.\n"
        "- If no intentions are present, return an empty array.\n\n"
        f"Current profile: {json.dumps(profile, default=str)}\n"
        f"Existing memory: {json.dumps(existing_memory, default=str)}\n"
        f"User message: {user_message}\n"
        f"Assistant response: {assistant_response}\n"
    )

    model = get_chat_model(model_name)
    response = model.invoke(prompt)
    parsed = _parse_json_object(_normalize_model_content(getattr(response, "content", "")))
    if parsed is None:
        raise ValueError("Model did not return valid JSON")
    return parsed


def extract_conversation_updates(
    user_message: str,
    assistant_response: str,
    profile: dict[str, Any],
    existing_memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    memory_state = existing_memory or {}
    profile_updates: dict[str, Any] = {}
    memory_payload: dict[str, Any] = {
        "last_summary": _fallback_memory_summary(user_message),
        "key_intentions": _extract_intentions_from_message(user_message),
    }

    extracted_income = _extract_income_from_message(user_message)
    if extracted_income is not None:
        profile_updates["monthly_income"] = extracted_income

    for model_name in _candidate_models():
        try:
            extracted = _extract_memory_with_model(
                model_name,
                user_message,
                assistant_response,
                profile,
                memory_state,
            )
            if not extracted:
                break

            model_profile_updates = _sanitize_profile_updates(
                extracted.get("profile_updates", {})
            )
            profile_updates.update(model_profile_updates)

            model_memory = _sanitize_memory(extracted.get("memory", {}))
            if model_memory:
                memory_payload.update(model_memory)
            break
        except ChatGoogleGenerativeAIError as exc:
            if _is_model_not_found_error(exc):
                logger.warning("Gemini model unavailable for memory extraction: %s", model_name)
                continue
            if _is_quota_exceeded_error(exc):
                logger.warning("Gemini quota exceeded during memory extraction")
                break
            logger.warning(
                "Gemini extraction failed; using fallback memory extraction",
                exc_info=exc,
            )
            break
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Memory extraction failed; using fallback memory extraction",
                exc_info=exc,
            )
            break

    return {
        "profile_updates": profile_updates,
        "memory": memory_payload,
    }


def run_financial_agent(message: str, profile: dict[str, Any]) -> str:
    if not settings.google_genai_api_key:
        raise RuntimeError("GOOGLE_GENAI_API_KEY is not configured")

    profile_context = _profile_to_context(profile)
    system_prompt = (
        "You are Egyptian Financial Advisor, a cautious and practical financial assistant. "
        "ALWAYS use the provided user profile context first before giving advice. "
        "Never invent facts, prices, rates, or news. "
        "For factual market/economic claims, call tools before answering.\n\n"
        "Tool usage policy:\n"
        "1) Database first: use query_financial_database for topics covered by the data pipeline "
        "(stocks, ticker performance, historical stats, gold, USD/EGP, macro indicators, CBE policy rates, and bank CD rates).\n"
        "2) Use search_web_with_gemini for requests outside database coverage, or when the user asks for live breaking news/latest updates not present in the database.\n"
        "3) Hybrid requests: if a question needs both historical/database facts and fresh web context, call BOTH relevant tools before answering.\n"
        "4) If a tool reports missing/empty data, say that clearly and then use the other suitable tool.\n"
        "5) In the final answer, clearly separate database findings from web-search findings and add a brief risk-aware recommendation.\n\n"
        "Use concise, clear language and include risk-aware caveats.\n\n"
        f"User profile context from Firestore (must be used first): {profile_context}"
    )

    last_error: Exception | None = None
    model_candidates = _candidate_models()

    for model_name in model_candidates:
        try:
            result = _invoke_agent_with_model(model_name, message, system_prompt)
            if model_name != model_candidates[0]:
                logger.warning(
                    "Fell back to Gemini model '%s' after configured model failed",
                    model_name,
                )
            return _extract_final_text(result)
        except ChatGoogleGenerativeAIError as exc:
            last_error = exc
            if _is_model_not_found_error(exc):
                logger.warning("Gemini model unavailable: %s", model_name)
                continue
            if _is_quota_exceeded_error(exc):
                retry_after_seconds = _extract_retry_after_seconds(exc)
                raise QuotaExceededError(
                    (
                        "Gemini API quota has been exceeded. "
                        "Please retry later or upgrade your Gemini API quota."
                    ),
                    retry_after_seconds=retry_after_seconds,
                ) from exc
            raise RuntimeError("Gemini request failed. Please try again shortly.") from exc

    raise RuntimeError(
        "No available Gemini model was found. "
        "Set GOOGLE_GENAI_MODEL to a supported value such as gemini-2.0-flash."
    ) from last_error
