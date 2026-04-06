WITH source AS (
    SELECT * FROM {{ source('efa_raw', 'raw_gold') }}
),

renamed_and_cast AS (
    SELECT
        -- Gold only needs the date for its primary key (one entry per day)
        CAST(FARM_FINGERPRINT(CAST(date AS STRING)) AS STRING) AS gold_daily_id,
        CAST(date AS DATE) AS market_date,
        
        -- Egyptian prices
        CAST(gold_24k_egp AS FLOAT64) AS gold_24k_egp,
        CAST(gold_21k_egp AS FLOAT64) AS gold_21k_egp,
        CAST(gold_18k_egp AS FLOAT64) AS gold_18k_egp,
        CAST(gold_14k_egp AS FLOAT64) AS gold_14k_egp,
        CAST(gold_12k_egp AS FLOAT64) AS gold_12k_egp,
        CAST(gold_10k_egp AS FLOAT64) AS gold_10k_egp,
        CAST(gold_9k_egp AS FLOAT64) AS gold_9k_egp,
        
        -- Global price
        CAST(global_ounce_usd AS FLOAT64) AS global_ounce_usd,
        
        -- Metadata
        CAST(extracted_at AS TIMESTAMP) AS _kestra_loaded_at
    FROM source
),

deduplicated AS (
    SELECT * FROM renamed_and_cast
    QUALIFY ROW_NUMBER() OVER(
        PARTITION BY market_date 
        ORDER BY _kestra_loaded_at DESC
    ) = 1
)

SELECT * FROM deduplicated