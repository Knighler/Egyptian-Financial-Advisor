import yfinance as yf
import pandas as pd
from datetime import datetime
import os

def extract_usd_egp():
    
    print("Fetching USD to EGP exchange rate...")
    ticker = yf.Ticker("EGP=X")
    
    # Get the last 1 day of data
    hist = ticker.history(period="1d")
    
    if hist.empty:
        raise ValueError("Failed to fetch exchange rate data.")
        
    # Extract the closing price
    current_rate = hist['Close'].iloc[-1]
    date = hist.index[-1].strftime('%Y-%m-%d')
    
    # Format as a DataFrame
    df = pd.DataFrame({
        'date': [date],
        'currency_pair': ['USD/EGP'],
        'exchange_rate': [round(current_rate, 2)],
        'extracted_at': [datetime.now().isoformat()]
    })
    
    os.makedirs("./data", exist_ok=True)
    file_path = "./data/usd_egp_latest.csv"
    df.to_csv(file_path, index=False)
    print(f"Saved exchange rate to {file_path}")
    

if __name__ == "__main__":
    extract_usd_egp()