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
from app.tools.market_tools import get_daily_pulse, get_ticker_performance

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


def _profile_to_context(profile: dict[str, Any]) -> str:
    allowed = {
        "monthly_income": profile.get("monthly_income"),
        "savings": profile.get("savings"),
        "investment_goal": profile.get("investment_goal"),
        "risk_tolerance": profile.get("risk_tolerance"),
    }
    return json.dumps(allowed, default=str)


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
        tools=[get_ticker_performance, get_daily_pulse],
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


def run_financial_agent(message: str, profile: dict[str, Any]) -> str:
    if not settings.google_genai_api_key:
        raise RuntimeError("GOOGLE_GENAI_API_KEY is not configured")

    profile_context = _profile_to_context(profile)
    system_prompt = (
        "You are Egyptian Financial Advisor, a cautious and practical financial assistant. "
        "ALWAYS use the provided user profile context first before giving advice. "
        "If market claims require data, call available tools before answering. "
        "Use concise, clear language and include risk-aware caveats. "
        "Do not fabricate numbers.\n\n"
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
