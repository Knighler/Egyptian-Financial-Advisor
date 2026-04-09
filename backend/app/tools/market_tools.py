import json
from typing import Any

from google.cloud import bigquery
from langchain_core.tools import tool

from app.core.config import settings
from app.services.bigquery_client import run_select_query


def _to_json(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No rows found."
    return json.dumps(rows, default=str)


def _qualified_table(table_name: str) -> str:
    if not settings.google_cloud_project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is not configured")
    return f"{settings.google_cloud_project}.{settings.bigquery_dataset}.{table_name}"


@tool
def get_ticker_performance(ticker_symbol: str) -> str:
    """Get the latest 7d/30d return and volatility snapshot for one EGX ticker."""
    cleaned = ticker_symbol.strip().upper()
    if not cleaned:
        return "Ticker symbol is required."

    table = _qualified_table("dim_ticker_performance")

    sql = f"""
SELECT
  ticker,
  last_updated,
  current_price,
  volatility_30d,
  return_7d_pct,
  return_30d_pct
FROM `{table}`
WHERE UPPER(ticker) = @ticker_symbol
LIMIT 1
""".strip()

    params = [bigquery.ScalarQueryParameter("ticker_symbol", "STRING", cleaned)]
    rows = run_select_query(sql, params)
    return _to_json(rows)


@tool
def get_daily_pulse() -> str:
    """Get latest market day snapshot across tickers with macro context columns."""
    table = _qualified_table("fct_daily_asset_performance")

    sql = f"""
SELECT
  market_date,
  ticker,
  close_price_egp,
  trading_volume,
  gold_24k_egp,
  official_usd_egp_rate,
  close_price_usd,
  local_gold_premium_ratio
FROM `{table}`
WHERE market_date = (
  SELECT MAX(market_date)
        FROM `{table}`
)
ORDER BY trading_volume DESC
LIMIT 20
""".strip()

    rows = run_select_query(sql)
    return _to_json(rows)
