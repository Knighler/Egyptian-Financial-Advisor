import json
import logging
import re
from typing import Any

from google.api_core.exceptions import NotFound
from google.cloud import bigquery
from langchain_core.tools import tool

from app.core.config import settings
from app.services.bigquery_client import run_select_query

logger = logging.getLogger(__name__)


TOPIC_TABLE_CANDIDATES: dict[str, tuple[str, ...]] = {
    "daily_market_pulse": ("fct_daily_asset_performance",),
    "ticker_performance": ("dim_ticker_performance", "stg_efa__stocks", "raw_stocks"),
    "historical_stats": ("fct_historical_stats", "historical_stocks", "raw_stocks"),
    "egx_stocks": ("stg_efa__stocks", "raw_stocks", "egx_stocks_latest", "historical_stocks"),
    "gold_prices": ("stg_efa__gold", "raw_gold", "egypt_gold_latest", "historical_gold"),
    "usd_egp": ("stg_efa__exchange", "raw_exchange", "usd_egp_latest", "historical_exchange"),
    "macro_indicators": (
        "macro_indicators",
        "macro_indicators_latest",
        "raw_macro_indicators",
    ),
    "cbe_policy_rates": ("cbe_rates_latest", "raw_cbe_rates", "cbe_rates"),
    "bank_cd_rates": ("bank_cds_latest", "raw_bank_cds", "bank_cds"),
}

TOPIC_ALIASES: dict[str, str] = {
    "pulse": "daily_market_pulse",
    "daily_pulse": "daily_market_pulse",
    "market_pulse": "daily_market_pulse",
    "ticker": "ticker_performance",
    "ticker_returns": "ticker_performance",
    "returns": "ticker_performance",
    "historical": "historical_stats",
    "stocks": "egx_stocks",
    "egx": "egx_stocks",
    "gold": "gold_prices",
    "exchange": "usd_egp",
    "usd": "usd_egp",
    "usd_egp_rates": "usd_egp",
    "fx": "usd_egp",
    "macro": "macro_indicators",
    "inflation": "macro_indicators",
    "gdp": "macro_indicators",
    "cbe": "cbe_policy_rates",
    "interest_rates": "cbe_policy_rates",
    "policy_rates": "cbe_policy_rates",
    "cd": "bank_cd_rates",
    "bank_cd": "bank_cd_rates",
    "certificate": "bank_cd_rates",
}

DEFAULT_DATASET_CANDIDATES = ("efa_main_main", "efa_main", "efa_raw_dataset", "efa_raw")


def _to_json_payload(payload: Any) -> str:
    return json.dumps(payload, default=str)


def _to_json(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No rows found."
    return json.dumps(rows, default=str)


def _qualified_table(table_name: str) -> str:
    if not settings.google_cloud_project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is not configured")
    return f"{settings.google_cloud_project}.{settings.bigquery_dataset}.{table_name}"


def _qualified_table_for_dataset(dataset: str, table_name: str) -> str:
    if not settings.google_cloud_project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is not configured")
    return f"{settings.google_cloud_project}.{dataset}.{table_name}"


def _candidate_datasets() -> list[str]:
    candidates: list[str] = []
    configured_dataset = (settings.bigquery_dataset or "").strip()
    for dataset in (configured_dataset, *DEFAULT_DATASET_CANDIDATES):
        if dataset and dataset not in candidates:
            candidates.append(dataset)
    return candidates


def _normalize_topic(topic: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", topic.strip().lower()).strip("_")
    if normalized in TOPIC_TABLE_CANDIDATES:
        return normalized
    return TOPIC_ALIASES.get(normalized, normalized)


def _is_not_found_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        isinstance(exc, NotFound)
        or "not found" in message
        or "dataset location mismatch" in message
    )


def _get_table_columns(dataset: str, table_name: str) -> list[str]:
    project = (settings.google_cloud_project or "").strip()
    if not project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is not configured")

    sql = f"""
SELECT column_name
FROM `{project}.{dataset}.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = @table_name
ORDER BY ordinal_position
""".strip()

    params = [bigquery.ScalarQueryParameter("table_name", "STRING", table_name)]
    try:
        rows = run_select_query(sql, params)
    except Exception as exc:  # noqa: BLE001
        if _is_not_found_error(exc):
            return []
        raise

    return [str(row["column_name"]).lower() for row in rows if row.get("column_name")]


def _pick_select_columns(columns: list[str]) -> list[str]:
    preferred = [
        "market_date",
        "date",
        "year",
        "last_updated",
        "ticker",
        "symbol",
        "currency_pair",
        "metric",
        "bank_name",
        "product",
        "rate",
        "deposit_rate",
        "lending_rate",
        "main_operation_rate",
        "last_meeting_date",
        "current_price",
        "close_price_egp",
        "closing_price_egp",
        "trading_volume",
        "volume",
        "gold_24k_egp",
        "global_ounce_usd",
        "exchange_rate",
        "official_usd_egp_rate",
        "return_7d_pct",
        "return_30d_pct",
        "volatility_30d",
        "historical_volatility",
        "average_daily_volume",
        "extraction_date",
        "extracted_at",
        "_kestra_loaded_at",
    ]

    selected: list[str] = []
    for column in preferred:
        if column in columns and column not in selected:
            selected.append(column)

    for column in columns:
        if column not in selected:
            selected.append(column)

    return selected[:12]


def _build_topic_query(
    full_table: str,
    columns: list[str],
    ticker_symbol: str,
    metric: str,
    limit: int,
) -> tuple[str, list[bigquery.ScalarQueryParameter]]:
    select_columns = _pick_select_columns(columns)
    filters: list[str] = []
    params: list[bigquery.ScalarQueryParameter] = []

    cleaned_ticker = ticker_symbol.strip().upper()
    if cleaned_ticker:
        if "ticker" in columns:
            filters.append("UPPER(ticker) = @ticker_symbol")
            params.append(
                bigquery.ScalarQueryParameter("ticker_symbol", "STRING", cleaned_ticker)
            )
        elif "symbol" in columns:
            filters.append("UPPER(symbol) = @ticker_symbol")
            params.append(
                bigquery.ScalarQueryParameter("ticker_symbol", "STRING", cleaned_ticker)
            )

    cleaned_metric = metric.strip().lower()
    if cleaned_metric and "metric" in columns:
        filters.append("LOWER(metric) = @metric")
        params.append(bigquery.ScalarQueryParameter("metric", "STRING", cleaned_metric))

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

    order_by_clause = ""
    for candidate in (
        "market_date",
        "date",
        "last_updated",
        "year",
        "extraction_date",
        "extracted_at",
        "_kestra_loaded_at",
    ):
        if candidate in columns:
            order_by_clause = f"ORDER BY {candidate} DESC"
            break

    row_limit = max(1, min(limit, 50))
    sql = f"""
SELECT
  {", ".join(select_columns)}
FROM `{full_table}`
{where_clause}
{order_by_clause}
LIMIT {row_limit}
""".strip()
    return sql, params


@tool
def get_available_database_topics() -> str:
    """List the supported database topics that query_financial_database can answer."""
    return _to_json_payload(
        {
            "topics": sorted(TOPIC_TABLE_CANDIDATES.keys()),
            "aliases": TOPIC_ALIASES,
        }
    )


@tool
def query_financial_database(
    topic: str,
    ticker_symbol: str = "",
    metric: str = "",
    limit: int = 20,
) -> str:
    """Query BigQuery for supported finance topics (stocks, gold, USD/EGP, macro, CBE rates, and bank CD rates). Use this first for factual numeric answers."""
    canonical_topic = _normalize_topic(topic)
    topic_tables = TOPIC_TABLE_CANDIDATES.get(canonical_topic)

    if not topic_tables:
        return _to_json_payload(
            {
                "status": "unsupported_topic",
                "requested_topic": topic,
                "supported_topics": sorted(TOPIC_TABLE_CANDIDATES.keys()),
            }
        )

    empty_sources: list[str] = []

    for table_name in topic_tables:
        for dataset in _candidate_datasets():
            full_table = _qualified_table_for_dataset(dataset, table_name)
            columns = _get_table_columns(dataset, table_name)
            if not columns:
                continue

            sql, params = _build_topic_query(
                full_table=full_table,
                columns=columns,
                ticker_symbol=ticker_symbol,
                metric=metric,
                limit=limit,
            )

            try:
                rows = run_select_query(sql, params)
            except Exception as exc:  # noqa: BLE001
                if _is_not_found_error(exc):
                    continue
                logger.warning(
                    "Database query failed for %s (%s): %s",
                    canonical_topic,
                    full_table,
                    exc,
                )
                continue

            if rows:
                return _to_json_payload(
                    {
                        "status": "ok",
                        "topic": canonical_topic,
                        "source": {
                            "table": full_table,
                            "filters": {
                                "ticker_symbol": ticker_symbol or None,
                                "metric": metric or None,
                            },
                        },
                        "rows": rows,
                    }
                )

            empty_sources.append(full_table)

    if empty_sources:
        return _to_json_payload(
            {
                "status": "empty",
                "topic": canonical_topic,
                "message": "Tables were found but no rows matched the requested filters.",
                "sources_checked": empty_sources,
            }
        )

    return _to_json_payload(
        {
            "status": "missing",
            "topic": canonical_topic,
            "message": (
                "No matching table was found in configured datasets. "
                "Use web search for this request, or ingest this topic into BigQuery."
            ),
            "datasets_checked": _candidate_datasets(),
            "table_candidates": list(topic_tables),
        }
    )


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


@tool
def get_historical_stats(ticker_symbol: str) -> str:
    """Get long-run context for one EGX ticker (all-time high/low, average price, historical volatility, and average volume)."""
    cleaned = ticker_symbol.strip().upper()
    if not cleaned:
        return "Ticker symbol is required."

    table = _qualified_table("fct_historical_stats")

    sql = f"""
SELECT
  ticker,
  data_start_date,
  data_end_date,
  all_time_high_egp,
  all_time_low_egp,
  historical_avg_price_egp,
  historical_volatility,
  average_daily_volume
FROM `{table}`
WHERE UPPER(ticker) = @ticker_symbol
LIMIT 1
""".strip()

    params = [bigquery.ScalarQueryParameter("ticker_symbol", "STRING", cleaned)]
    rows = run_select_query(sql, params)
    return _to_json(rows)
