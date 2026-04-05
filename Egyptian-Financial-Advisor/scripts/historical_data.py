import yfinance as yf
import pandas as pd
from datetime import datetime
import os

def run_historical_backfill():
    print("Starting Massive 5-Year Historical Backfill...")
    os.makedirs("data", exist_ok=True)
    
    # --- 1. HISTORICAL EXCHANGE RATES ---
    print("Fetching USD/EGP history...")
    egp_hist = yf.Ticker("EGP=X").history(period="5y")
    egp_rows = []
    for date, row in egp_hist.iterrows():
        egp_rows.append({
            'date': date.strftime('%Y-%m-%d'),
            'currency_pair': 'USD/EGP',
            'exchange_rate': round(row['Close'], 2),
            'extracted_at': datetime.now().isoformat()
        })
    pd.DataFrame(egp_rows).to_csv("data/historical_exchange.csv", index=False)

    # --- 2. HISTORICAL GOLD PRICES ---
    print("Fetching Global Gold history and calculating EGP fair value...")
    gold_hist = yf.Ticker("GC=F").history(period="5y")
    
    # We must merge Gold and EGP on exact dates to calculate historical local prices
    df_gold = gold_hist[['Close']].rename(columns={'Close': 'global_ounce_usd'})
    df_egp = egp_hist[['Close']].rename(columns={'Close': 'usd_egp'})
    df_merged = df_gold.join(df_egp, how='inner').dropna()

    gold_rows = []
    for date, row in df_merged.iterrows():
        gold_usd_gram = row['global_ounce_usd'] / 31.1034
        gold_24k_egp = gold_usd_gram * row['usd_egp']
        gold_rows.append({
            'date': date.strftime('%Y-%m-%d'),
            'gold_24k_egp': round(gold_24k_egp, 2),
            'gold_21k_egp': round(gold_24k_egp * (21/24), 2),
            'gold_18k_egp': round(gold_24k_egp * (18/24), 2),
            'gold_14k_egp': round(gold_24k_egp * (14/24), 2),
            'gold_12k_egp': round(gold_24k_egp * (12/24), 2),
            'gold_10k_egp': round(gold_24k_egp * (10/24), 2),
            'gold_9k_egp': round(gold_24k_egp* (9/24), 2),
            'global_ounce_usd': round(row['global_ounce_usd'], 2),
            'extracted_at': datetime.now().isoformat()
        })
    pd.DataFrame(gold_rows).to_csv("data/historical_gold.csv", index=False)

    # --- 3. HISTORICAL EGX STOCKS ---
    print("Fetching EGX Stocks history (This will take a few minutes)...")
    with open("config/egx_tickers.txt", "r") as file:
        tickers = [line.strip() for line in file if line.strip()]
        
    stock_rows = []
    for symbol in tickers:
        try:
            hist = yf.Ticker(symbol).history(period="5y")
            for date, row in hist.iterrows():
                stock_rows.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'symbol': symbol,
                    'closing_price_egp': round(row['Close'], 2),
                    'volume': int(row['Volume']),
                    'extracted_at': datetime.now().isoformat()
                })
        except Exception as e:
            print(f"Skipped {symbol} or missing historical data.")

    df_stocks = pd.DataFrame(stock_rows)
    df_stocks.to_csv("data/historical_stocks.csv", index=False)
    
    print(f"Total Stock Records: {len(df_stocks)}")

if __name__ == "__main__":
    run_historical_backfill()