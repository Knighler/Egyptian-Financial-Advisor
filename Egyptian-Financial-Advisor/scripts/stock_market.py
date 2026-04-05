import yfinance as yf
import pandas as pd
from datetime import datetime
import os

def extract_egx_stocks():
    print("Fetching EGX stock data")
    
    # Dynamically find the project root
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(base_dir, ".."))
    
    config_path = os.path.join(project_root, "config", "egx_tickers.txt")
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Missing {config_path}. Please create it and add your tickers.")
        
    with open(config_path, "r") as file:
        egx_tickers = [line.strip() for line in file if line.strip()]
        
    print(f"Loaded {len(egx_tickers)} tickers from config file.")
    
    data_rows = []

    for symbol in egx_tickers:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            
            if not hist.empty:
                data_rows.append({
                    'date': hist.index[-1].strftime('%Y-%m-%d'),
                    'symbol': symbol,
                    'closing_price_egp': round(hist['Close'].iloc[-1], 2),
                    'volume': int(hist['Volume'].iloc[-1]),
                    'extracted_at': datetime.now().isoformat()
                })
            else:
                print(f"Warning: No data found for {symbol}")
                
        except Exception as e:
            # If one stock fails, print an error but keep going!
            print(f"Skipping {symbol} due to error: {e}")
            
    df = pd.DataFrame(data_rows)
    
    data_dir = os.path.join(project_root, "data")
    os.makedirs(data_dir, exist_ok=True)
    file_path = os.path.join(data_dir, "egx_stocks_latest.csv")
    
    # Only save if we actually got data
    if not df.empty:
        df.to_csv(file_path, index=False)
        print(f"Successfully saved {len(df)} stock records to {file_path}")
    else:
        print("Pipeline failed: No stock data was retrieved.")

if __name__ == "__main__":
    extract_egx_stocks()