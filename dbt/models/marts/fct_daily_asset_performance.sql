WITH stocks AS (
    SELECT * FROM {{ ref('stg_efa__stocks') }}
),

gold AS (
    SELECT * FROM {{ ref('stg_efa__gold') }}
),

exchange AS (
    SELECT * FROM {{ ref('stg_efa__exchange') }}
    WHERE currency_pair = 'USD/EGP' -- Or whatever your exact pair string is
)

SELECT
    s.stock_daily_id,
    s.market_date,
    s.ticker,
    
    -- Stock Metrics
    s.close_price_egp,
    s.trading_volume,
    
    -- Macro Environment on that exact day
    g.gold_24k_egp,
    g.global_ounce_usd,
    e.exchange_rate AS official_usd_egp_rate,
    
    -- Agentic Features (Calculated columns the AI will love)
    -- 1. What is the stock worth in USD today?
    ROUND(s.close_price_egp / NULLIF(e.exchange_rate, 0), 2) AS close_price_usd,
    
    -- 2. "The Gold Premium": Is gold heavily overpriced in Egypt right now?
    -- (Local Gold Price / Global Ounce Price) / Official USD Rate
    -- If this is > 1.0, the black market / local valuation of USD is higher than official.
    ROUND((g.gold_24k_egp * 31.1035 / NULLIF(g.global_ounce_usd, 0)) / NULLIF(e.exchange_rate, 0), 3) AS local_gold_premium_ratio

FROM stocks s
LEFT JOIN gold g ON s.market_date = g.market_date
LEFT JOIN exchange e ON s.market_date = e.market_date