import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# File paths for saving data
DATA_DIR = "data"
DRAFT_DATA_FILE = os.path.join(DATA_DIR, "draft_data.csv")
SCHEDULE_DATA_FILE = os.path.join(DATA_DIR, "schedule_data.csv")
SCRAPE_METADATA_FILE = os.path.join(DATA_DIR, "scrape_metadata.json")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Helper functions for Eastern timezone
def get_eastern_now():
    """Get current datetime in Eastern timezone"""
    return datetime.now(ZoneInfo("America/New_York"))

def get_eastern_today():
    """Get today's date in Eastern timezone"""
    return get_eastern_now().date()


# =================================================================== Scrape NBA Draft Board
def scrape_nba_mock_draft(url):
    """Scrape NBA draft board tables"""
    print(f"Scraping NBA Draft Board from {url}...")
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    all_data = []  # List to store data from both tables

    for table_id in ["nba_mock_consensus_table", "nba_mock_consensus_table2"]:
        table = soup.find("table", {"id": table_id})
        if table:
            rows = table.find("tbody").find_all("tr")
            for row in rows:
                cols = row.find_all("td")
                cols = [col.text.strip() for col in cols]
                all_data.append(cols)  # Append data to the common list

    df = pd.DataFrame(all_data)  # Create DataFrame from combined data
    # Assign column names (assuming they are the same for both tables)
    df.columns = ["Rank", "Team", "Player", "H", "W", "P", "School", "C"]
    print(f"✓ Scraped {len(df)} draft prospects")
    return df


# =================================================================== Scrape NCAA Schedule

# Helper function to extract cell content (handles both text and images)
def extract_cell_content(cell):
    """Extract content from a table cell, checking for images (TV logos) first"""
    # Check if cell contains an image (common for TV networks)
    img = cell.find("img")
    if img:
        # Try to get alt text first
        alt_text = img.get("alt", "")
        
        # Only use alt text if it looks like a real network name (not base64 placeholder)
        # ESPN uses lazy loading with base64 placeholders like "YH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
        if alt_text and len(alt_text) < 20 and not alt_text.startswith("YH5"):
            return alt_text.strip()
        
        # If no valid alt text, try to extract from src URL
        src = img.get("src", "")
        if src and "network" in src:
            # Extract network name from URL like "/i/network/espn_plus.png" -> "ESPN+"
            parts = src.split("/")
            if parts:
                filename = parts[-1].replace(".png", "").replace(".jpg", "").replace("_", " ")
                return filename.strip().upper()
    
    # Fall back to text content
    return cell.text.strip()


# Function to scrape a single date
def scrape_single_date(single_date):
    """Scrape NCAA schedule for a single date"""
    date_str = single_date.strftime("%Y%m%d")
    url = f"https://www.espn.com/mens-college-basketball/schedule/_/date/{date_str}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")
        
        table = soup.find("table")
        if not table:
            return None
        
        rows = table.find_all("tr")
        # Use helper function to extract content from each cell
        data = [[extract_cell_content(col) for col in row.find_all(["th", "td"])] for row in rows if row.find_all(["th", "td"])]
        
        df = pd.DataFrame(data)
        if not df.empty:
            df.columns = df.iloc[0]
            df = df.drop(0).reset_index(drop=True)
            df.columns = [df.columns[0]] + [''] + list(df.columns[1:-1])
            df["DATE"] = single_date.strftime("%Y-%m-%d")
            return df.to_dict('records')
    except Exception as e:
        print(f"Error scraping {date_str}: {e}")
        return None


# Main function to scrape NCAA schedule
def scrape_ncaa_schedule(days=30):
    """Scrape NCAA schedule for the next N days"""
    print(f"Scraping NCAA schedule for next {days} days...")
    
    dates_to_scrape = []
    for i in range(days):
        single_date = get_eastern_today() + timedelta(days=i)
        dates_to_scrape.append(single_date)
    
    # Scrape dates in parallel
    all_data = {}
    print(f"Scraping {len(dates_to_scrape)} dates in parallel...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_date = {executor.submit(scrape_single_date, d): d for d in dates_to_scrape}
        
        for future in as_completed(future_to_date):
            single_date = future_to_date[future]
            try:
                result = future.result()
                if result:
                    date_str = single_date.strftime("%Y-%m-%d")
                    all_data[date_str] = result
                    print(f"✓ Scraped {date_str}")
            except Exception as e:
                print(f"✗ Error processing {single_date}: {e}")
    
    # Convert to DataFrame
    all_records = []
    for date_str in sorted(all_data.keys()):
        all_records.extend(all_data[date_str])
    
    combined_df = pd.DataFrame(all_records)
    if not combined_df.empty:
        combined_df['DATE'] = pd.to_datetime(combined_df['DATE']).dt.date
        # Rename columns to proper names before saving
        combined_df = combined_df.rename(columns={
            'MATCHUP': 'AWAY',
            '': 'HOME',
            'tickets': 'TICKETS',
            'location': 'LOCATION',
            'logo espnbet': 'ODDS_BY'
        })
    
    print(f"✓ Total games scraped: {len(combined_df)}")
    return combined_df


# =================================================================== Main Scraping Function

def run_scraper():
    """Run all scrapers and save data to files"""
    print("\n" + "="*60)
    print("Starting Web Scraper")
    print("="*60 + "\n")
    
    scrape_time = get_eastern_now().isoformat()
    
    # Scrape NBA Draft Board
    draft_url = "https://www.nbadraft.net/nba-mock-drafts/?year-mock=2026"
    draft_df = scrape_nba_mock_draft(draft_url)
    
    # Save draft data
    draft_df.to_csv(DRAFT_DATA_FILE, index=False)
    print(f"✓ Saved draft data to {DRAFT_DATA_FILE}\n")
    
    # Scrape NCAA Schedule
    schedule_df = scrape_ncaa_schedule(days=30)
    
    # Save schedule data
    schedule_df.to_csv(SCHEDULE_DATA_FILE, index=False)
    print(f"✓ Saved schedule data to {SCHEDULE_DATA_FILE}\n")
    
    # Save metadata
    metadata = {
        "last_scrape_time": scrape_time,
        "draft_prospects_count": len(draft_df),
        "games_count": len(schedule_df),
        "scraper_version": "1.0"
    }
    with open(SCRAPE_METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"✓ Saved metadata to {SCRAPE_METADATA_FILE}\n")
    
    print("="*60)
    print("Scraping Complete!")
    print(f"Last scraped: {scrape_time}")
    print(f"Draft prospects: {len(draft_df)}")
    print(f"Games: {len(schedule_df)}")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_scraper()
