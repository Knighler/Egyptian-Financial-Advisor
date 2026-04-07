WITH daily_data AS (
    SELECT * FROM {{ ref('fct_daily_asset_performance') }}
),

windowed_calculations AS (
    SELECT
        ticker,
        market_date,
        close_price_egp,
        trading_volume,
        
        -- Look back 7 and 30 days to grab the old prices
        LAG(close_price_egp, 7) OVER (PARTITION BY ticker ORDER BY market_date) AS price_7d_ago,
        LAG(close_price_egp, 30) OVER (PARTITION BY ticker ORDER BY market_date) AS price_30d_ago,
        
        -- Calculate Volatility (Standard deviation over the last 30 days)
        STDDEV(close_price_egp) OVER (
            PARTITION BY ticker 
            ORDER BY market_date 
            ROWS BETWEEN 30 PRECEDING AND CURRENT ROW
        ) AS volatility_30d
        
    FROM daily_data
),

latest_records AS (
    -- Keep ONLY the most recent day for each ticker
    SELECT * FROM windowed_calculations
    QUALIFY ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY market_date DESC) = 1
)

SELECT
    ticker,
    market_date AS last_updated,
    close_price_egp AS current_price,
    volatility_30d,
    
    -- Calculate the exact percentage return for the AI to read
    ROUND(((close_price_egp - price_7d_ago) / NULLIF(price_7d_ago, 0)) * 100, 2) AS return_7d_pct,
    ROUND(((close_price_egp - price_30d_ago) / NULLIF(price_30d_ago, 0)) * 100, 2) AS return_30d_pct

FROM latest_records