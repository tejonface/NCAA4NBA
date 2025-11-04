import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
import json
import os
import shutil
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


# =================================================================== Data Management Helpers

def backup_file(filepath):
    """Create a backup of an existing file before overwriting"""
    if os.path.exists(filepath):
        backup_path = filepath + ".backup"
        shutil.copy2(filepath, backup_path)
        print(f"✓ Created backup: {backup_path}")
        return backup_path
    return None

def save_with_atomic_write(df, filepath, description="data"):
    """Save DataFrame with atomic write (save to temp, then rename)
    
    This prevents partial/corrupted files if the script crashes during write.
    """
    temp_path = filepath + ".tmp"
    
    # Save to temporary file first
    df.to_csv(temp_path, index=False)
    
    # Rename temp file to final destination (atomic operation)
    os.replace(temp_path, filepath)
    print(f"✓ Saved {description} to {filepath}")

def validate_data(df, min_rows=1, data_type="data"):
    """Validate that scraped data meets basic quality checks"""
    if df is None or df.empty:
        raise ValueError(f"{data_type} is empty - scraping may have failed")
    
    if len(df) < min_rows:
        raise ValueError(f"{data_type} has only {len(df)} rows (expected at least {min_rows})")
    
    print(f"✓ Validation passed: {data_type} has {len(df)} rows")
    return True


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


# Function to scrape a specific date range
def scrape_date_range(start_date, end_date):
    """Scrape NCAA schedule for a specific date range
    
    Args:
        start_date: date object for start of range
        end_date: date object for end of range
    
    Returns:
        DataFrame with games in the date range
    """
    print(f"Scraping date range: {start_date} to {end_date}")
    
    all_data = {}
    batch_dates = []
    current_date = start_date
    
    while current_date <= end_date:
        batch_dates.append(current_date)
        current_date += timedelta(days=1)
    
    print(f"Scraping {len(batch_dates)} dates...")
    
    # Scrape in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_date = {executor.submit(scrape_single_date, d): d for d in batch_dates}
        
        for future in as_completed(future_to_date):
            single_date = future_to_date[future]
            try:
                result = future.result()
                date_str = single_date.strftime("%Y-%m-%d")
                
                if result:
                    all_data[date_str] = result
                    print(f"✓ Scraped {date_str} ({len(result)} games)")
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
    
    print(f"✓ Scraped {len(combined_df)} games from {len(all_data)} dates with games")
    return combined_df


# Main function to scrape NCAA schedule
def scrape_ncaa_schedule(max_consecutive_empty=10):
    """Scrape NCAA schedule until we hit max_consecutive_empty days with no games
    
    This ensures we capture the entire season without hardcoding an end date.
    The season typically ends in early April, but this approach handles variations.
    """
    print(f"Scraping NCAA schedule until {max_consecutive_empty} consecutive days with no games...")
    
    all_data = {}
    all_dates_scraped = []
    batch_size = 30
    day_offset = 0
    consecutive_empty = 0
    
    # Keep scraping in batches until we hit the consecutive empty threshold
    while consecutive_empty < max_consecutive_empty and day_offset < 365:
        # Prepare next batch of dates
        batch_dates = []
        for i in range(batch_size):
            single_date = get_eastern_today() + timedelta(days=day_offset)
            batch_dates.append(single_date)
            day_offset += 1
        
        print(f"Scraping batch starting at day {day_offset - batch_size} ({len(batch_dates)} dates)...")
        
        # Scrape this batch in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_date = {executor.submit(scrape_single_date, d): d for d in batch_dates}
            
            for future in as_completed(future_to_date):
                single_date = future_to_date[future]
                try:
                    result = future.result()
                    date_str = single_date.strftime("%Y-%m-%d")
                    all_dates_scraped.append(date_str)
                    
                    if result:
                        all_data[date_str] = result
                        print(f"✓ Scraped {date_str} ({len(result)} games)")
                except Exception as e:
                    print(f"✗ Error processing {single_date}: {e}")
        
        # Check consecutive empty days at the END of what we've scraped so far
        # Sort all dates we've checked
        sorted_dates = sorted(all_dates_scraped)
        consecutive_empty = 0
        
        # Count consecutive empty days from the most recent dates
        for date_str in reversed(sorted_dates):
            if date_str not in all_data:
                consecutive_empty += 1
            else:
                # Found a date with games, reset counter
                consecutive_empty = 0
        
        if consecutive_empty >= max_consecutive_empty:
            print(f"✓ Found {consecutive_empty} consecutive days with no games - stopping scrape")
            break
    
    if day_offset >= 365:
        print("⚠ Reached 365-day safety limit")
    
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
    
    print(f"✓ Total games scraped: {len(combined_df)} across {len(all_data)} dates with games")
    return combined_df


# =================================================================== Smart Update Functions

def load_metadata():
    """Load scrape metadata from file"""
    if os.path.exists(SCRAPE_METADATA_FILE):
        with open(SCRAPE_METADATA_FILE, 'r') as f:
            return json.load(f)
    return {
        "last_scrape_time": None,
        "draft_prospects_count": 0,
        "games_count": 0,
        "scraper_version": "2.0",
        "last_today_scrape": None,
        "last_nearfuture_scrape": None,
        "last_full_scrape": None
    }


def update_schedule_partial(date_range_name, start_date, end_date):
    """Update only a specific date range in the schedule
    
    Args:
        date_range_name: "today", "nearfuture" (next 7 days), or "full"
        start_date: Start date for scraping
        end_date: End date for scraping
    
    Returns:
        True if update succeeded, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"Partial Schedule Update: {date_range_name}")
    print(f"Date range: {start_date} to {end_date}")
    print("="*60 + "\n")
    
    try:
        # Scrape the new data for this range
        new_data = scrape_date_range(start_date, end_date)
        
        if new_data.empty:
            print(f"⚠ No games found in range {start_date} to {end_date}")
            return False
        
        # Load existing schedule data
        if os.path.exists(SCHEDULE_DATA_FILE):
            existing_df = pd.read_csv(SCHEDULE_DATA_FILE)
            existing_df['DATE'] = pd.to_datetime(existing_df['DATE']).dt.date
            
            # Remove old data from this date range
            existing_df = existing_df[
                (existing_df['DATE'] < start_date) | (existing_df['DATE'] > end_date)
            ]
            
            # Combine with new data
            combined_df = pd.concat([existing_df, new_data], ignore_index=True)
            combined_df = combined_df.sort_values('DATE').reset_index(drop=True)
        else:
            combined_df = new_data
        
        # Save updated schedule
        backup_file(SCHEDULE_DATA_FILE)
        save_with_atomic_write(combined_df, SCHEDULE_DATA_FILE, f"schedule data ({date_range_name})")
        
        # Update metadata
        metadata = load_metadata()
        metadata[f"last_{date_range_name}_scrape"] = get_eastern_now().isoformat()
        metadata["games_count"] = len(combined_df)
        
        temp_metadata_path = SCRAPE_METADATA_FILE + ".tmp"
        with open(temp_metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        os.replace(temp_metadata_path, SCRAPE_METADATA_FILE)
        
        print(f"\n✓ Updated {date_range_name} schedule: {len(new_data)} games")
        print("="*60 + "\n")
        return True
        
    except Exception as e:
        print(f"\n✗ Error updating {date_range_name} schedule: {e}")
        print("="*60 + "\n")
        return False


def update_draft_data():
    """Update draft board data
    
    Returns:
        True if update succeeded, False otherwise
    """
    print(f"\n{'='*60}")
    print("Updating Draft Board")
    print("="*60 + "\n")
    
    try:
        draft_url = "https://www.nbadraft.net/nba-mock-drafts/?year-mock=2026"
        draft_df = scrape_nba_mock_draft(draft_url)
        
        validate_data(draft_df, min_rows=30, data_type="Draft prospects")
        
        backup_file(DRAFT_DATA_FILE)
        save_with_atomic_write(draft_df, DRAFT_DATA_FILE, "draft data")
        
        # Update metadata
        metadata = load_metadata()
        metadata["draft_prospects_count"] = len(draft_df)
        metadata["last_scrape_time"] = get_eastern_now().isoformat()
        
        temp_metadata_path = SCRAPE_METADATA_FILE + ".tmp"
        with open(temp_metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        os.replace(temp_metadata_path, SCRAPE_METADATA_FILE)
        
        print(f"\n✓ Updated draft data: {len(draft_df)} prospects")
        print("="*60 + "\n")
        return True
        
    except Exception as e:
        print(f"\n✗ Error updating draft data: {e}")
        print("="*60 + "\n")
        return False


# =================================================================== Main Scraping Function

def run_scraper():
    """Run all scrapers and save data to files with validation and atomic writes"""
    print("\n" + "="*60)
    print("Starting Web Scraper")
    print("="*60 + "\n")
    
    scrape_time = get_eastern_now().isoformat()
    
    try:
        # Scrape NBA Draft Board
        draft_url = "https://www.nbadraft.net/nba-mock-drafts/?year-mock=2026"
        draft_df = scrape_nba_mock_draft(draft_url)
        
        # Validate draft data (expect at least 30 prospects)
        validate_data(draft_df, min_rows=30, data_type="Draft prospects")
        
        # Backup existing draft file before overwriting
        backup_file(DRAFT_DATA_FILE)
        
        # Save draft data with atomic write
        save_with_atomic_write(draft_df, DRAFT_DATA_FILE, "draft data")
        print()
        
        # Scrape NCAA Schedule (continues until 10 consecutive days with no games)
        schedule_df = scrape_ncaa_schedule(max_consecutive_empty=10)
        
        # Validate schedule data (expect at least 100 games for the season)
        validate_data(schedule_df, min_rows=100, data_type="Schedule games")
        
        # Backup existing schedule file before overwriting
        backup_file(SCHEDULE_DATA_FILE)
        
        # Save schedule data with atomic write
        save_with_atomic_write(schedule_df, SCHEDULE_DATA_FILE, "schedule data")
        print()
        
        # Save metadata with atomic write
        metadata = {
            "last_scrape_time": scrape_time,
            "draft_prospects_count": len(draft_df),
            "games_count": len(schedule_df),
            "scraper_version": "2.0",
            "last_today_scrape": scrape_time,
            "last_nearfuture_scrape": scrape_time,
            "last_full_scrape": scrape_time
        }
        
        backup_file(SCRAPE_METADATA_FILE)
        temp_metadata_path = SCRAPE_METADATA_FILE + ".tmp"
        with open(temp_metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        os.replace(temp_metadata_path, SCRAPE_METADATA_FILE)
        print(f"✓ Saved metadata to {SCRAPE_METADATA_FILE}\n")
        
        print("="*60)
        print("Scraping Complete!")
        print(f"Last scraped: {scrape_time}")
        print(f"Draft prospects: {len(draft_df)}")
        print(f"Games: {len(schedule_df)}")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"ERROR: Scraping failed - {str(e)}")
        print(f"{'='*60}\n")
        print("Previous data files remain intact (not overwritten)")
        raise


if __name__ == "__main__":
    run_scraper()
