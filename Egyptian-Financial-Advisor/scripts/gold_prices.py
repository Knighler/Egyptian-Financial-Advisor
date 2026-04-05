import yfinance as yf
import pandas as pd
from datetime import datetime
import os

def extract_gold_prices():
    print("Calculating Egyptian Gold prices...")
    
    gold_ticker = yf.Ticker("GC=F")
    gold_hist = gold_ticker.history(period="5d")
    
    if gold_hist.empty:
        raise ValueError("Failed to fetch Gold data from Yahoo Finance.")
        
    global_gold_usd_ounce = gold_hist['Close'].iloc[-1]
    last_trading_date = gold_hist.index[-1].strftime('%Y-%m-%d')
    
    egp_ticker = yf.Ticker("EGP=X")
    egp_hist = egp_ticker.history(period="5d")
    
    if egp_hist.empty:
        raise ValueError("Failed to fetch EGP exchange rate data.")
        
    usd_to_egp_rate = egp_hist['Close'].iloc[-1]

    gold_usd_gram = global_gold_usd_ounce / 31.1034 
    
    gold_24k_egp = gold_usd_gram * usd_to_egp_rate
    standard_karats = [24, 22, 21, 18, 14, 12, 10, 9]
    gold_prices_by_karat = {
        f'gold_{karat}k_egp': [round(gold_24k_egp * (karat / 24), 2)]
        for karat in standard_karats
    }
    
    df = pd.DataFrame({
        'date': [last_trading_date],
        **gold_prices_by_karat,
        'global_ounce_usd': [round(global_gold_usd_ounce, 2)],
        'extracted_at': [datetime.now().isoformat()]
    })
    
    # Dynamically find the project root and data directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(base_dir, ".."))
    data_dir = os.path.join(project_root, "data")
    
    os.makedirs(data_dir, exist_ok=True)
    file_path = os.path.join(data_dir, "egypt_gold_latest.csv")
    df.to_csv(file_path, index=False)
    print(f"Saved gold prices to {file_path}")

if __name__ == "__main__":
    extract_gold_prices()