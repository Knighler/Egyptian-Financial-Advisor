WITH source AS (
    SELECT * FROM {{ source('efa_raw', 'raw_exchange') }}
),

renamed_and_cast AS (
    SELECT
        CAST(FARM_FINGERPRINT(CONCAT(CAST(date AS STRING), currency_pair)) AS STRING) AS exchange_daily_id,
        CAST(date AS DATE) AS market_date,
        CAST(currency_pair AS STRING) AS currency_pair,
        CAST(exchange_rate AS FLOAT64) AS exchange_rate,
        CAST(extracted_at AS TIMESTAMP) AS _kestra_loaded_at
    FROM source
),

deduplicated AS (
    SELECT * FROM renamed_and_cast
    QUALIFY ROW_NUMBER() OVER(
        PARTITION BY market_date, currency_pair 
        ORDER BY _kestra_loaded_at DESC
    ) = 1
)

SELECT * FROM deduplicated