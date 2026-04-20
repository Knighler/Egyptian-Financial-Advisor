import requests
import pandas as pd
import os
from datetime import datetime

def get_world_bank_data():
    indicators = {
        "inflation": "FP.CPI.TOTL.ZG",
        "gdp_growth": "NY.GDP.MKTP.KD.ZG"
    }
    results = []
    
    for name, code in indicators.items():
        url = f"https://api.worldbank.org/v2/country/EGY/indicator/{code}?format=json"
        response = requests.get(url).json()
        # The first valid data point is usually at index 1 of the result list
        latest_data = next(item for item in response[1] if item["value"] is not None)
        results.append({
            "metric": name,
            "value": round(latest_data["value"], 2),
            "year": latest_data["date"],
            "extraction_date": datetime.now().strftime("%Y-%m-%d")
        })
    
    return pd.DataFrame(results)

if __name__ == "__main__":
    df = get_world_bank_data()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(base_dir, ".."))
    data_dir = os.path.join(project_root, "data")
    
    os.makedirs(data_dir, exist_ok=True)
    file_path = os.path.join(data_dir, "macro_indicators.csv")
    df.to_csv(file_path, index=False)
    print(f"Saved Macro data to {file_path}")
    print("Inflation and GDP data updated via World Bank API.")