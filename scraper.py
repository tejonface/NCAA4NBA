"""
NBA Prospect Schedule Scraper
Scrapes data from nbadraft.net and ESPN, stores in PostgreSQL database
Run this script daily to keep data updated
"""

import os
import psycopg2
from psycopg2.extras import execute_values
import requests
from bs4 import BeautifulSoup
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# Database connection
DATABASE_URL = os.environ.get('DATABASE_URL')

# NBA team logos
NBA_TEAM_LOGOS = {
    "Atlanta": "https://a.espncdn.com/i/teamlogos/nba/500/atl.png",
    "Boston": "https://a.espncdn.com/i/teamlogos/nba/500/bos.png",
    "Brooklyn": "https://a.espncdn.com/i/teamlogos/nba/500/bkn.png",
    "Charlotte": "https://a.espncdn.com/i/teamlogos/nba/500/cha.png",
    "Chicago": "https://a.espncdn.com/i/teamlogos/nba/500/chi.png",
    "Cleveland": "https://a.espncdn.com/i/teamlogos/nba/500/cle.png",
    "Dallas": "https://a.espncdn.com/i/teamlogos/nba/500/dal.png",
    "Denver": "https://a.espncdn.com/i/teamlogos/nba/500/den.png",
    "Detroit": "https://a.espncdn.com/i/teamlogos/nba/500/det.png",
    "Golden St.": "https://a.espncdn.com/i/teamlogos/nba/500/gs.png",
    "Golden State": "https://a.espncdn.com/i/teamlogos/nba/500/gs.png",
    "Houston": "https://a.espncdn.com/i/teamlogos/nba/500/hou.png",
    "Indiana": "https://a.espncdn.com/i/teamlogos/nba/500/ind.png",
    "LA Clippers": "https://a.espncdn.com/i/teamlogos/nba/500/lac.png",
    "LA Lakers": "https://a.espncdn.com/i/teamlogos/nba/500/lal.png",
    "Memphis": "https://a.espncdn.com/i/teamlogos/nba/500/mem.png",
    "Miami": "https://a.espncdn.com/i/teamlogos/nba/500/mia.png",
    "Milwaukee": "https://a.espncdn.com/i/teamlogos/nba/500/mil.png",
    "Minnesota": "https://a.espncdn.com/i/teamlogos/nba/500/min.png",
    "New Orleans": "https://a.espncdn.com/i/teamlogos/nba/500/no.png",
    "New York": "https://a.espncdn.com/i/teamlogos/nba/500/ny.png",
    "Oklahoma Cty": "https://a.espncdn.com/i/teamlogos/nba/500/okc.png",
    "Oklahoma City": "https://a.espncdn.com/i/teamlogos/nba/500/okc.png",
    "Orlando": "https://a.espncdn.com/i/teamlogos/nba/500/orl.png",
    "Philadelphia": "https://a.espncdn.com/i/teamlogos/nba/500/phi.png",
    "Phoenix": "https://a.espncdn.com/i/teamlogos/nba/500/phx.png",
    "Portland": "https://a.espncdn.com/i/teamlogos/nba/500/por.png",
    "Sacramento": "https://a.espncdn.com/i/teamlogos/nba/500/sac.png",
    "San Antonio": "https://a.espncdn.com/i/teamlogos/nba/500/sa.png",
    "Toronto": "https://a.espncdn.com/i/teamlogos/nba/500/tor.png",
    "Utah": "https://a.espncdn.com/i/teamlogos/nba/500/utah.png",
    "Washington": "https://a.espncdn.com/i/teamlogos/nba/500/wsh.png"
}

def get_eastern_now():
    """Get current datetime in Eastern timezone"""
    return datetime.now(ZoneInfo("America/New_York"))

def get_eastern_today():
    """Get today's date in Eastern timezone"""
    return get_eastern_now().date()

def get_team_logo(team_name):
    """Get logo URL for a team, stripping asterisks"""
    if not team_name or team_name == "":
        return ""
    clean_name = team_name.strip().replace("*", "")
    return NBA_TEAM_LOGOS.get(clean_name, "")

def scrape_nba_mock_draft(url):
    """Scrape NBA draft board from nbadraft.net"""
    print("Scraping NBA mock draft...")
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    
    all_data = []
    for table_id in ["nba_mock_consensus_table", "nba_mock_consensus_table2"]:
        table = soup.find("table", {"id": table_id})
        if table:
            rows = table.find("tbody").find_all("tr")
            for row in rows:
                cols = row.find_all("td")
                cols = [col.text.strip() for col in cols]
                all_data.append(cols)
    
    prospects = []
    for row in all_data:
        if len(row) >= 8:
            rank, team, player, height, weight, position, school, conference = row[:8]
            prospects.append({
                'rank': int(rank) if rank.isdigit() else 0,
                'team': team,
                'team_logo_url': get_team_logo(team),
                'player': player,
                'height': height,
                'weight': weight,
                'position': position,
                'school': school,
                'conference': conference
            })
    
    print(f"Found {len(prospects)} prospects")
    return prospects

def extract_cell_content(cell):
    """Extract content from table cell (handles TV logos)"""
    img = cell.find("img")
    if img:
        alt_text = img.get("alt", "")
        if alt_text and len(alt_text) < 20 and not alt_text.startswith("YH5"):
            return alt_text.strip()
        src = img.get("src", "")
        if src and "network" in src:
            parts = src.split("/")
            if parts:
                filename = parts[-1].replace(".png", "").replace(".jpg", "").replace("_", " ")
                return filename.strip().upper()
    return cell.text.strip()

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
            return []
        
        rows = table.find_all("tr")
        data = [[extract_cell_content(col) for col in row.find_all(["th", "td"])] for row in rows if row.find_all(["th", "td"])]
        
        games = []
        if data:
            # Skip header row
            for row in data[1:]:
                if len(row) >= 2:
                    matchup = row[0]
                    time = row[1] if len(row) > 1 else ""
                    tv = row[2] if len(row) > 2 else ""
                    
                    # Parse matchup
                    if " @ " in matchup:
                        parts = matchup.split(" @ ")
                        away = parts[0].strip()
                        home = parts[1].strip() if len(parts) > 1 else ""
                        
                        games.append({
                            'game_date': single_date,
                            'game_time': time,
                            'away_team': away,
                            'home_team': home,
                            'tv_network': tv
                        })
        
        return games
    except Exception as e:
        print(f"Error scraping {date_str}: {e}")
        return []

def scrape_ncaa_schedule():
    """Scrape NCAA schedule for next 60 days"""
    print("Scraping NCAA schedule...")
    today = get_eastern_today()
    yesterday = today - timedelta(days=1)
    dates_to_scrape = [yesterday + timedelta(days=i) for i in range(61)]
    
    all_games = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_date = {executor.submit(scrape_single_date, d): d for d in dates_to_scrape}
        for future in as_completed(future_to_date):
            games = future.result()
            if games:
                all_games.extend(games)
    
    print(f"Found {len(all_games)} games")
    return all_games

def save_to_database(prospects, games):
    """Save scraped data to PostgreSQL"""
    print("Saving to database...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    try:
        # Clear existing data
        cur.execute("DELETE FROM game_prospects")
        cur.execute("DELETE FROM games")
        cur.execute("DELETE FROM prospects")
        
        # Insert prospects
        prospect_data = [(
            p['rank'], p['team'], p['team_logo_url'], p['player'],
            p['height'], p['weight'], p['position'], p['school'], p['conference']
        ) for p in prospects]
        
        execute_values(cur, """
            INSERT INTO prospects (rank, team, team_logo_url, player, height, weight, position, school, conference)
            VALUES %s
        """, prospect_data)
        
        # Insert games
        game_data = [(
            g['game_date'], g['game_time'], g['away_team'], g['home_team'], g['tv_network']
        ) for g in games]
        
        execute_values(cur, """
            INSERT INTO games (game_date, game_time, away_team, home_team, tv_network)
            VALUES %s
            ON CONFLICT (game_date, away_team, home_team) DO UPDATE
            SET game_time = EXCLUDED.game_time, tv_network = EXCLUDED.tv_network
        """, game_data)
        
        # Link prospects to games
        # Normalize school names for matching
        cur.execute("SELECT id, school FROM prospects")
        prospect_schools = {normalize_team(school): pid for pid, school in cur.fetchall()}
        
        cur.execute("SELECT id, game_date, away_team, home_team FROM games")
        for game_id, game_date, away_team, home_team in cur.fetchall():
            away_norm = normalize_team(away_team)
            home_norm = normalize_team(home_team)
            
            # Match prospects
            for school_norm, prospect_id in prospect_schools.items():
                if school_norm == away_norm:
                    cur.execute("""
                        INSERT INTO game_prospects (game_id, prospect_id, team)
                        VALUES (%s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (game_id, prospect_id, away_team))
                elif school_norm == home_norm:
                    cur.execute("""
                        INSERT INTO game_prospects (game_id, prospect_id, team)
                        VALUES (%s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (game_id, prospect_id, home_team))
        
        conn.commit()
        print("✓ Data saved successfully")
        
    except Exception as e:
        conn.rollback()
        print(f"Error saving to database: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def normalize_team(team_name):
    """Normalize team name for matching"""
    if not team_name:
        return ""
    normalized = team_name.strip()
    # Remove rankings
    normalized = ''.join(c for c in normalized if not c.isdigit()).strip()
    normalized = normalized.replace('@', '').strip()
    # Normalize St. -> State, St -> Saint
    normalized = normalized.replace('St.', 'State').replace(' St ', ' Saint ')
    # Remove apostrophes
    normalized = normalized.replace("'", "")
    return normalized.lower()

if __name__ == "__main__":
    print("Starting NBA Prospect Schedule scraper...")
    draft_url = "https://www.nbadraft.net/nba-mock-drafts/?year-mock=2026"
    
    prospects = scrape_nba_mock_draft(draft_url)
    games = scrape_ncaa_schedule()
    save_to_database(prospects, games)
    
    print("✓ Scraping complete!")
