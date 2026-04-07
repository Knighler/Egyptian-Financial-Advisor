WITH daily_data AS (
    SELECT * FROM {{ ref('fct_daily_asset_performance') }}
)

SELECT
    ticker,
    MIN(market_date) AS data_start_date,
    MAX(market_date) AS data_end_date,
    
    -- 5-Year Highs and Lows
    MAX(close_price_egp) AS all_time_high_egp,
    MIN(close_price_egp) AS all_time_low_egp,
    ROUND(AVG(close_price_egp), 2) AS historical_avg_price_egp,
    
    -- How erratic is this stock generally?
    ROUND(STDDEV(close_price_egp), 2) AS historical_volatility,
    
    -- Volume context
    ROUND(AVG(trading_volume), 0) AS average_daily_volume

FROM daily_data
GROUP BY ticker