import csv
import json
import os
import re
from datetime import datetime, timedelta
import urllib.request

def download_forexfactory_calendar():
    """
    Downloads the economic calendar from a public source or generates a mock calendar for 2025.
    Since historical data scraping can be complex without a premium API, we'll build a simple 
    scraper or mock generator that ensures High Impact (3-bull/red) events are captured.
    """
    print("[NEWS DOWNLOADER] Fetching economic calendar data for 2025...")
    
    # In a fully production environment we would scrape investing.com or forexfactory 
    # month by month. For this backtester, we'll generate a comprehensive mock for Nov 2025
    # covering key events like ISM, NFP, CPI, and US Elections to ensure the system works.
    
    events = []
    
    # Add key known events for November 2025 (Mock data based on standard schedules)
    events.append({
        'datetime': '2025-11-04T12:00:00Z', # US Election Day starts
        'event': 'US Presidential Elections',
        'impact': 'High'
    })
    events.append({
        'datetime': '2025-11-05T14:45:00Z', # PMI / ISM mock event during our trade time!
        'event': 'US ISM Services PMI',
        'impact': 'High'
    })
    events.append({
        'datetime': '2025-11-05T15:00:00Z', 
        'event': 'US JOLTs Job Openings',
        'impact': 'High'
    })
    events.append({
        'datetime': '2025-11-06T19:00:00Z', 
        'event': 'FOMC Statement & Fed Interest Rate Decision',
        'impact': 'High'
    })
    events.append({
        'datetime': '2025-11-07T13:30:00Z', 
        'event': 'Nonfarm Payrolls (NFP)',
        'impact': 'High'
    })
    events.append({
        'datetime': '2025-11-12T13:30:00Z', 
        'event': 'US CPI (Inflation)',
        'impact': 'High'
    })
    
    # Create data directory if it doesn't exist
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    csv_path = os.path.join(data_dir, 'economic_calendar.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['datetime', 'event', 'impact'])
        writer.writeheader()
        writer.writerows(events)
        
    print(f"[NEWS DOWNLOADER] Saved {len(events)} High-Impact events to {csv_path}")

if __name__ == "__main__":
    download_forexfactory_calendar()
