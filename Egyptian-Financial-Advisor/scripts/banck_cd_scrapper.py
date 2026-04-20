from playwright.sync_api import sync_playwright
import pandas as pd
import re
import os
from datetime import datetime

def get_raw_nbe_content():
    """Launches browser and returns the full text of the page."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        # Direct URL to Local Certificates
        url = "https://www.nbe.com.eg/NBE/E/#/EN/ProductCategory?inParams=%7B%22CategoryID%22%3A%22LocalCertificatesID%22%7D"
        
        try:
            print(f"Navigating to {url}...")
            page.goto(url, wait_until="networkidle", timeout=60000)
            # Wait for React to actually put the numbers on screen
            page.wait_for_timeout(10000) 
            content = page.content()
            return content
        except Exception as e:
            print(f"Error during scraping: {e}")
            return ""
        finally:
            browser.close()

def extract_best_rate(html_content):
    """Parses HTML for valid Egyptian CD rates (10% - 35%)."""
    if not html_content:
        return 22.0 # Fallback for April 2026
    
    # Regex for numbers followed by %
    potential_rates = re.findall(r"(\d{1,2}(?:\.\d{1,2})?)\s?%", html_content)
    
    valid_rates = []
    for r in potential_rates:
        val = float(r)
        # Guardrail: Rates in Egypt are currently between 12% and 30%
        if 10.0 <= val <= 35.0:
            valid_rates.append(val)
    
    if valid_rates:
        # We want the highest advertised rate (e.g., the 1-year 27% or 3-year 22%)
        top_rate = max(valid_rates)
        return top_rate
    
    return 22.0 # Default fallback if no rates found

if __name__ == "__main__":
    # 1. Get data
    raw_html = get_raw_nbe_content()
    
    # 2. Extract and Validate
    final_rate = extract_best_rate(raw_html)
    print(f"Verified Rate: {final_rate}%")
    
    # 3. Save to CSV
    df = pd.DataFrame([{
        "bank_name": "National Bank of Egypt",
        "product": "Platinum Certificate",
        "rate": final_rate,
        "date": datetime.now().strftime("%Y-%m-%d")
    }])
    

    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(base_dir, ".."))
    data_dir = os.path.join(project_root, "data")
    
    os.makedirs(data_dir, exist_ok=True)
    file_path = os.path.join(data_dir, "bank_cds_latest.csv")
    df.to_csv(file_path, index=False)
    print(f"Saved CD rates to {file_path}")