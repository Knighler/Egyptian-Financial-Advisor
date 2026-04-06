WITH source AS (
    SELECT * FROM {{ source('efa_raw', 'raw_stocks') }}
),

renamed_and_cast AS (
    SELECT
        -- Generate a Surrogate Primary Key using Date and Symbol
        CAST(FARM_FINGERPRINT(CONCAT(CAST(date AS STRING), symbol)) AS STRING) AS stock_daily_id,

        -- Standardize Dimensions
        CAST(date AS DATE) AS market_date,
        CAST(symbol AS STRING) AS ticker,

        -- Cast Metrics exactly as they are in your schema
        CAST(closing_price_egp AS FLOAT64) AS close_price_egp,
        CAST(volume AS INT64) AS trading_volume,

        -- Keep the metadata
        CAST(extracted_at AS TIMESTAMP) AS _kestra_loaded_at

    FROM source
),

deduplicated AS (
    -- Remove duplicates in case Kestra triggers the same daily flow twice
    SELECT *
    FROM renamed_and_cast
    QUALIFY ROW_NUMBER() OVER(
        PARTITION BY market_date, ticker 
        ORDER BY _kestra_loaded_at DESC
    ) = 1
)

SELECT * FROM deduplicated