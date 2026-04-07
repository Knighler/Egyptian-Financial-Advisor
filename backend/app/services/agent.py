import json
from functools import lru_cache
from typing import Any

from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.tools.market_tools import get_daily_pulse, get_ticker_performance


def _profile_to_context(profile: dict[str, Any]) -> str:
    allowed = {
        "monthly_income": profile.get("monthly_income"),
        "savings": profile.get("savings"),
        "investment_goal": profile.get("investment_goal"),
        "risk_tolerance": profile.get("risk_tolerance"),
    }
    return json.dumps(allowed, default=str)


@lru_cache(maxsize=1)
def get_chat_model() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=settings.google_genai_model,
        google_api_key=settings.google_genai_api_key,
        temperature=0.2,
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

    agent = create_agent(
        model=get_chat_model(),
        tools=[get_ticker_performance, get_daily_pulse],
        system_prompt=system_prompt,
    )

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": message,
                }
            ]
        }
    )

    return _extract_final_text(result)
