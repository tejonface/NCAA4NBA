"""
NBA Prospect Schedule Tracker - Self-Contained Version
Combines web scraping and display in a single file for Streamlit Cloud deployment
"""

import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import re
from concurrent.futures import ThreadPoolExecutor
import time

# ====================================================================================
# UTILITY FUNCTIONS
# ====================================================================================

def get_eastern_now():
    """Get current datetime in Eastern timezone"""
    return datetime.now(ZoneInfo("America/New_York"))

def get_eastern_today():
    """Get today's date in Eastern timezone"""
    return get_eastern_now().date()

def clean_team_name(team_name):
    """Clean and standardize team names for matching"""
    if pd.isna(team_name) or team_name == "":
        return ""
    cleaned = re.sub(r'[@0-9]', '', str(team_name)).strip()
    cleaned = re.sub(r'St\.$', 'State', cleaned)
    cleaned = re.sub(r'^St\.', 'Saint', cleaned)
    cleaned = cleaned.replace("'", "")
    return cleaned

def clean_team_name_series(series):
    """Clean and standardize team names in a pandas Series"""
    return series.apply(clean_team_name)

# ====================================================================================
# STATIC FALLBACK DATA (60 top 2026 NBA Draft prospects)
# ====================================================================================

STATIC_DRAFT_DATA = [
    {'Rank': 1, 'Team': '*Utah', 'Player': 'AJ Dybantsa', 'School': 'BYU'},
    {'Rank': 2, 'Team': '*Washington', 'Player': 'Darryn Peterson', 'School': 'Kansas'},
    {'Rank': 3, 'Team': 'Charlotte', 'Player': 'Mikel Brown', 'School': 'Louisville'},
    {'Rank': 4, 'Team': 'New Orleans', 'Player': 'Cameron Boozer', 'School': 'Duke'},
    {'Rank': 5, 'Team': '*Philadelphia', 'Player': 'Caleb Wilson', 'School': 'North Carolina'},
    {'Rank': 6, 'Team': 'Brooklyn', 'Player': 'Kam Williams', 'School': 'Kentucky'},
    {'Rank': 7, 'Team': 'Toronto', 'Player': 'Chris Cenac', 'School': 'Houston'},
    {'Rank': 8, 'Team': 'San Antonio', 'Player': 'Nate Ament', 'School': 'Tennessee'},
    {'Rank': 9, 'Team': 'Phoenix', 'Player': 'Isaiah Evans', 'School': 'Duke'},
    {'Rank': 10, 'Team': '*Portland', 'Player': 'Kingston Flemings', 'School': 'Houston'},
    {'Rank': 11, 'Team': '*Miami', 'Player': 'Johann Grunloh', 'School': 'Virginia'},
    {'Rank': 12, 'Team': 'Dallas', 'Player': 'Karter Knox', 'School': 'Arkansas'},
    {'Rank': 13, 'Team': '*San Antonio', 'Player': 'Karim Lopez', 'School': 'Mexico'},
    {'Rank': 14, 'Team': 'Sacramento', 'Player': 'Ian Jackson', 'School': 'St. Johns'},
    {'Rank': 15, 'Team': 'Atlanta', 'Player': 'Boogie Fland', 'School': 'Florida'},
    {'Rank': 16, 'Team': 'Orlando', 'Player': 'Jayden Quaintance', 'School': 'Kentucky'},
    {'Rank': 17, 'Team': 'Detroit', 'Player': 'Tounde Yessoufou', 'School': 'Baylor'},
    {'Rank': 18, 'Team': 'Golden St.', 'Player': 'Miles Byrd', 'School': 'San Diego St.'},
    {'Rank': 19, 'Team': 'Memphis', 'Player': 'Labaron Philon', 'School': 'Alabama'},
    {'Rank': 20, 'Team': 'Milwaukee', 'Player': 'Matt Able', 'School': 'NC State'},
    {'Rank': 21, 'Team': 'Minnesota', 'Player': 'Alijah Arenas', 'School': 'USC'},
    {'Rank': 22, 'Team': 'LA Lakers', 'Player': 'Hannes Steinbach', 'School': 'Washington'},
    {'Rank': 23, 'Team': 'Indiana', 'Player': 'Brayden Burries', 'School': 'Arizona'},
    {'Rank': 24, 'Team': 'Denver', 'Player': 'Dash Daniels', 'School': 'Australia'},
    {'Rank': 25, 'Team': 'LA Clippers', 'Player': 'Meleek Thomas', 'School': 'Arkansas'},
    {'Rank': 26, 'Team': 'New York', 'Player': 'Bennett Stirtz', 'School': 'Iowa'},
    {'Rank': 27, 'Team': 'Houston', 'Player': 'Yaxel Lendeborg', 'School': 'Michigan'},
    {'Rank': 28, 'Team': 'Boston', 'Player': 'Thomas Haugh', 'School': 'Florida'},
    {'Rank': 29, 'Team': 'Cleveland', 'Player': 'JT Toppin', 'School': 'Texas Tech'},
    {'Rank': 30, 'Team': 'Oklahoma Cty', 'Player': 'Dame Sarr', 'School': 'Duke'},
    {'Rank': 31, 'Team': 'Utah', 'Player': 'Luigi Suigo', 'School': 'Italy'},
    {'Rank': 32, 'Team': 'Washington', 'Player': 'Neoklis Avdalas', 'School': 'Virginia Tech'},
    {'Rank': 33, 'Team': 'Charlotte', 'Player': 'Milos Uzan', 'School': 'Houston'},
    {'Rank': 34, 'Team': 'New Orleans', 'Player': 'Baye Ndongo', 'School': 'Georgia Tech'},
    {'Rank': 35, 'Team': 'Philadelphia', 'Player': 'Jaron Pierre', 'School': 'SMU'},
    {'Rank': 36, 'Team': 'Brooklyn', 'Player': 'Zuby Ejiofor', 'School': 'St. Johns'},
    {'Rank': 37, 'Team': 'Toronto', 'Player': 'Richie Saunders', 'School': 'BYU'},
    {'Rank': 38, 'Team': 'San Antonio', 'Player': 'Michael Ruzic', 'School': 'Croatia'},
    {'Rank': 39, 'Team': 'Phoenix', 'Player': 'Malique Lewis', 'School': ''},
    {'Rank': 40, 'Team': 'Portland', 'Player': 'Sergio De Larrea', 'School': 'Spain'},
    {'Rank': 41, 'Team': 'Miami', 'Player': 'PJ Haggerty', 'School': 'Kansas State'},
    {'Rank': 42, 'Team': 'Dallas', 'Player': 'Amarion Dickerson', 'School': 'USC'},
    {'Rank': 43, 'Team': 'Chicago', 'Player': 'Alex Karaban', 'School': 'UConn'},
    {'Rank': 44, 'Team': 'Sacramento', 'Player': 'Noa Kouakou-Heugue', 'School': 'France'},
    {'Rank': 45, 'Team': 'Atlanta', 'Player': 'Baba Miller', 'School': 'Cincinnati'},
    {'Rank': 46, 'Team': 'Orlando', 'Player': 'Nate Bittle', 'School': 'Oregon'},
    {'Rank': 47, 'Team': 'Detroit', 'Player': 'Mackenzie Mgbako', 'School': 'Texas A&M'},
    {'Rank': 48, 'Team': 'Golden St.', 'Player': 'Mathias M\'Madi', 'School': 'Madigascar'},
    {'Rank': 49, 'Team': 'Memphis', 'Player': 'Robert Wright', 'School': 'BYU'},
    {'Rank': 50, 'Team': 'Milwaukee', 'Player': 'Tarris Reed', 'School': 'UConn'},
    {'Rank': 51, 'Team': 'Minnesota', 'Player': 'Jevon Porter', 'School': 'Missouri'},
    {'Rank': 52, 'Team': 'LA Lakers', 'Player': 'Seth Trimble', 'School': 'North Carolina'},
    {'Rank': 53, 'Team': 'Indiana', 'Player': 'Roddy Gayle', 'School': 'Michigan'},
    {'Rank': 54, 'Team': 'Denver', 'Player': 'Tre White', 'School': 'Kansas'},
    {'Rank': 55, 'Team': 'LA Clippers', 'Player': 'Donovan Dent', 'School': 'UCLA'},
    {'Rank': 56, 'Team': 'New York', 'Player': 'Xaivian Lee', 'School': 'Florida'},
    {'Rank': 57, 'Team': 'Houston', 'Player': 'Malik Reneau', 'School': 'Miami'},
    {'Rank': 58, 'Team': 'Boston', 'Player': 'JJ Starling', 'School': 'Syracuse'},
    {'Rank': 59, 'Team': 'Cleveland', 'Player': 'Ognjen Srzentic', 'School': 'Serbia'},
    {'Rank': 60, 'Team': 'Oklahoma Cty', 'Player': 'Otega Oweh', 'School': 'Kentucky'},
]

# ====================================================================================
# WEB SCRAPING FUNCTIONS
# ====================================================================================

@st.cache_data(ttl=7200, show_spinner="Scraping NBA Draft data...")
def scrape_nba_draft_data():
    """Scrape mock draft data from nbadraft.net

    Falls back to static_draft_data.csv if scraping fails.

    Returns:
        DataFrame with columns: Rank, Team, Player, School
    """
    url = "https://www.nbadraft.net/nba-mock-drafts/?year-mock=2026"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the consensus mock draft table
        tables = soup.find_all('table', {'id': ['nba_mock_consensus_table', 'nba_mock_consensus_table2']})

        if not tables:
            st.warning("Could not find draft table on nbadraft.net - using cached data")
            return load_static_draft_data()

        all_rows = []
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:  # Skip header
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 4:
                    rank = cols[0].get_text(strip=True)
                    team = cols[1].get_text(strip=True)
                    player = cols[2].get_text(strip=True)
                    school = cols[3].get_text(strip=True)

                    if rank and rank.isdigit():
                        all_rows.append({
                            'Rank': int(rank),
                            'Team': team,
                            'Player': player,
                            'School': school
                        })

        if all_rows:
            df = pd.DataFrame(all_rows)
            df = df.drop_duplicates(subset=['Rank', 'Player'])
            return df
        else:
            st.warning("No draft data found - using cached data")
            return load_static_draft_data()

    except Exception as e:
        st.warning(f"Error scraping draft data - using cached data")
        return load_static_draft_data()

def load_static_draft_data():
    """Load hardcoded static draft data as fallback

    Returns:
        DataFrame with draft data from hardcoded constant
    """
    return pd.DataFrame(STATIC_DRAFT_DATA)

def scrape_single_date_schedule(date_obj):
    """Scrape ESPN schedule for a single date

    Args:
        date_obj: date object to scrape

    Returns:
        List of game dictionaries
    """
    date_str = date_obj.strftime("%Y%m%d")
    url = f"https://www.espn.com/mens-college-basketball/schedule/_/date/{date_str}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the schedule table
        table = soup.find('table', class_='schedule')
        if not table:
            table = soup.find('div', class_='schedule')

        if not table:
            return []

        games = []
        rows = table.find_all('tr')

        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 3:
                try:
                    away = cells[0].get_text(strip=True)
                    home = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                    time_cell = cells[2] if len(cells) > 2 else None

                    # Extract time
                    time_text = "TBD"
                    if time_cell:
                        time_span = time_cell.find('span')
                        if time_span:
                            time_text = time_span.get_text(strip=True)
                        else:
                            time_text = time_cell.get_text(strip=True)

                    # Extract TV network
                    tv = ""
                    if len(cells) > 3:
                        tv_cell = cells[3]
                        tv_img = tv_cell.find('img')
                        if tv_img and tv_img.get('alt'):
                            tv = tv_img.get('alt')
                        else:
                            tv = tv_cell.get_text(strip=True)

                    if away and home and away != home:
                        games.append({
                            'DATE': date_obj,
                            'AWAY': away,
                            'HOME': home,
                            'TIME': time_text,
                            'TV': tv
                        })
                except:
                    continue

        return games
    except:
        return []

@st.cache_data(ttl=7200, show_spinner="Scraping NCAA schedule data...")
def scrape_ncaa_schedule():
    """Scrape NCAA basketball schedule from ESPN

    Returns:
        DataFrame with columns: DATE, AWAY, HOME, TIME, TV
    """
    today = get_eastern_today()
    all_games = []

    # Scrape next 60 days of schedule
    with ThreadPoolExecutor(max_workers=10) as executor:
        date_range = [today + timedelta(days=i) for i in range(60)]
        results = list(executor.map(scrape_single_date_schedule, date_range))

        for games in results:
            all_games.extend(games)

    if all_games:
        df = pd.DataFrame(all_games)
        df = df.drop_duplicates()
        return df
    else:
        return pd.DataFrame()

# ====================================================================================
# DATA TRANSFORMATION FUNCTIONS
# ====================================================================================

@st.cache_data(ttl=7200)
def prepare_draft_with_games(draft_df, schedule_df):
    """Merge draft data with upcoming games for each prospect

    Returns:
        DataFrame ready for Draft Board display
    """
    if draft_df.empty or schedule_df.empty:
        return pd.DataFrame()

    # Clean team names for matching
    draft_df = draft_df.copy()
    schedule_df = schedule_df.copy()

    draft_df['School_Merge'] = clean_team_name_series(draft_df['School'])
    schedule_df['HomeTeam'] = clean_team_name_series(schedule_df['HOME'])
    schedule_df['AwayTeam'] = clean_team_name_series(schedule_df['AWAY'])

    # Create rows for both home and away teams
    home_games = schedule_df.copy()
    home_games['TEAM'] = home_games['HomeTeam']

    away_games = schedule_df.copy()
    away_games['TEAM'] = away_games['AwayTeam']

    combined_schedule = pd.concat([home_games, away_games], ignore_index=True)

    # Filter to games with draft prospects
    prospect_games = combined_schedule[combined_schedule['TEAM'].isin(draft_df['School_Merge'])]

    # Merge with draft data
    merged = pd.merge(
        draft_df,
        prospect_games,
        left_on='School_Merge',
        right_on='TEAM',
        how='left'
    )

    # Select and organize columns
    result = merged[['Rank', 'Team', 'Player', 'School', 'DATE', 'TIME', 'TV', 'AWAY', 'HOME']]
    result = result.sort_values(by=['Rank', 'DATE'], ascending=[True, True])
    result = result.drop_duplicates(subset=['Rank', 'Player', 'School'])
    result = result.reset_index(drop=True)

    return result

@st.cache_data(ttl=7200)
def prepare_games_with_players(draft_df, schedule_df):
    """Add All_Players column showing prospects in each game

    Returns:
        DataFrame with All_Players column for Games by Date display
    """
    if draft_df.empty or schedule_df.empty:
        return pd.DataFrame()

    draft_df = draft_df.copy()
    schedule_df = schedule_df.copy()

    draft_df['School_Merge'] = clean_team_name_series(draft_df['School'])
    schedule_df['HomeTeam'] = clean_team_name_series(schedule_df['HOME'])
    schedule_df['AwayTeam'] = clean_team_name_series(schedule_df['AWAY'])

    def get_players_for_team(team_name):
        """Get all draft prospects from a team"""
        players = draft_df[draft_df['School_Merge'] == team_name][['Rank', 'Player', 'School']]
        return players.to_dict(orient='records')

    # Add players for both teams
    schedule_df['HomeTeam_Players'] = schedule_df['HomeTeam'].apply(get_players_for_team)
    schedule_df['AwayTeam_Players'] = schedule_df['AwayTeam'].apply(get_players_for_team)

    # Combine and format
    schedule_df['All_Players'] = schedule_df.apply(
        lambda row: row['HomeTeam_Players'] + row['AwayTeam_Players'], axis=1
    )

    schedule_df['All_Players'] = schedule_df.apply(
        lambda row: ', '.join([
            f"{p['School']}-#{str(p['Rank'])} {p['Player']}"
            for p in sorted(row['All_Players'], key=lambda x: int(x['Rank']))
        ]) if row['All_Players'] else '',
        axis=1
    )

    return schedule_df

@st.cache_data(ttl=7200)
def prepare_super_matchups(draft_df, games_with_players_df):
    """Filter to games with prospects on BOTH teams

    Returns:
        DataFrame for Super Matchups display
    """
    if draft_df.empty or games_with_players_df.empty:
        return pd.DataFrame()

    draft_df = draft_df.copy()
    games_df = games_with_players_df.copy()

    draft_df['School_Merge'] = clean_team_name_series(draft_df['School'])

    # Filter to games where both teams have prospects
    super_matchups = games_df[
        (games_df['HomeTeam'].isin(draft_df['School_Merge'])) &
        (games_df['AwayTeam'].isin(draft_df['School_Merge']))
    ]

    result = super_matchups[['AWAY', 'HOME', 'DATE', 'TIME', 'TV', 'All_Players']].drop_duplicates()
    return result

# ====================================================================================
# LOAD AND PREPARE ALL DATA
# ====================================================================================

# Show loading message
with st.spinner("Loading NBA Draft and NCAA Schedule data..."):
    # Scrape data (cached for 2 hours)
    draft_df = scrape_nba_draft_data()
    schedule_df = scrape_ncaa_schedule()

# Check if data loaded successfully
if draft_df.empty:
    st.error("⚠️ Could not load draft data. Please refresh the page or try again later.")
    st.stop()

if schedule_df.empty:
    st.warning("⚠️ Could not load schedule data. Showing draft board only.")

# Prepare transformed data
draft_with_games = prepare_draft_with_games(draft_df, schedule_df)
games_with_players = prepare_games_with_players(draft_df, schedule_df)
super_matchups = prepare_super_matchups(draft_df, games_with_players)

# Sort draft board by rank
if not draft_with_games.empty:
    draft_with_games = draft_with_games.sort_values(by='Rank', ascending=True).reset_index(drop=True)

# ====================================================================================
# NBA TEAM LOGOS
# ====================================================================================

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

def get_team_logo(team_name):
    """Get logo URL for a team, stripping asterisks and handling variations"""
    if pd.isna(team_name) or team_name == "":
        return ""
    clean_name = team_name.strip().replace("*", "")
    return NBA_TEAM_LOGOS.get(clean_name, "")

# Add team logos to draft board
if not draft_with_games.empty:
    draft_with_games['Team'] = draft_with_games['Team'].apply(get_team_logo)

# ====================================================================================
# LIVE GAME DETECTION
# ====================================================================================

def detect_live_games(row):
    """Detect if a game is live, upcoming, or final based on current time"""
    if pd.isna(row.get('DATE')) or pd.isna(row.get('TIME')):
        return ""

    try:
        date_obj = row['DATE'] if isinstance(row['DATE'], date) else pd.to_datetime(row['DATE']).date()
        time_str = str(row['TIME']).strip().upper()

        if time_str == 'LIVE':
            return "🔴 Live"

        if time_str in ['TBD', 'TBA', '']:
            return "TBD"

        current_et = get_eastern_now()
        today_et = current_et.date()

        if date_obj != today_et:
            month_day = date_obj.strftime('%b %-d')
            return f"{month_day}, {time_str}" if time_str not in ['TBD', 'TBA'] else f"{month_day}, TBD"

        try:
            from datetime import datetime as dt
            game_time_obj = dt.strptime(time_str, '%I:%M %p').time()
            game_datetime = datetime.combine(date_obj, game_time_obj, tzinfo=ZoneInfo("America/New_York"))

            time_diff = (current_et - game_datetime).total_seconds() / 60

            if -15 <= time_diff <= 180:
                return "🔴 Live"
            elif time_diff > 180:
                return "Final"
            else:
                return f"Today, {time_str}"
        except:
            return f"Today, {time_str}"

    except:
        return ""

def format_game_time(row):
    """Format DATE and TIME into readable format"""
    return detect_live_games(row)

# Add formatted game time to draft board
if not draft_with_games.empty:
    draft_with_games['Game Time (ET)'] = draft_with_games.apply(format_game_time, axis=1)

# ====================================================================================
# STREAMLIT UI
# ====================================================================================

st.set_page_config(layout="centered", page_title="NBA Prospect Schedule")

# Custom CSS
st.markdown("""
<style>
    :root {
        --primary-blue: #3b82f6;
        --primary-dark: #2563eb;
        --primary-light: #60a5fa;
        --bg-light: #f8fafc;
        --border-color: #e2e8f0;
        --text-primary: #1e293b;
        --text-secondary: #64748b;
    }
    
    .main .block-container {
        padding-top: 0.1rem;
        max-width: 1400px;
        margin: 0 auto;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        padding-top: 4px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 60px;
        background-color: var(--bg-light);
        border-radius: 8px 8px 0 0;
        padding: 12px 24px;
        font-size: 16px;
        font-weight: 500;
        color: var(--text-secondary);
        border: 1px solid var(--border-color);
    }
    
    .stTabs [aria-selected="true"] {
        background-color: var(--primary-blue);
        color: white;
        box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# Header
col_title, col_refresh = st.columns([5, 1])
with col_title:
    st.title("NBA Prospect Schedule")
with col_refresh:
    if st.button("🔄 Refresh", help="Clear cache and reload data"):
        st.cache_data.clear()
        st.rerun()

st.caption("Track upcoming NCAA games for 2026 NBA Draft prospects")
st.divider()

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["📋 Draft Board", "⭐ Super Matchups", "📅 Games by Date", "📊 Prospect Distribution"])

# TAB 1: Draft Board
with tab1:
    st.header("Draft Board with Next Games")
    st.caption("Top 60 prospects ranked with their next scheduled game.")

    if not draft_with_games.empty:
        display_df = draft_with_games.copy()
        display_df = display_df.rename(columns={'AWAY': 'Away', 'HOME': 'Home', 'Rank': 'Pick'})
        draft_display = display_df[['Pick', 'Team', 'Player', 'School', 'Game Time (ET)', 'TV', 'Away', 'Home']]

        st.dataframe(
            draft_display,
            hide_index=True,
            height=400,
            column_config={
                "Pick": st.column_config.NumberColumn("Pick", help="Mock draft pick number", width=45),
                "Team": st.column_config.ImageColumn("Team", help="NBA Team Logo", width=60),
                "Player": st.column_config.TextColumn("Player", width=120),
                "School": st.column_config.TextColumn("School", width=120),
                "Game Time (ET)": st.column_config.TextColumn("Game Time (ET)", width=110),
                "TV": st.column_config.TextColumn("TV", width=60),
                "Away": st.column_config.TextColumn("Away", width=120),
                "Home": st.column_config.TextColumn("Home", width=120)
            }
        )
    else:
        st.info("No draft data available")

# TAB 2: Super Matchups
with tab2:
    st.header("Super Matchups")
    st.caption("Games featuring prospects on both teams.")

    if not super_matchups.empty:
        super_df = super_matchups.copy()
        super_df['Game Time (ET)'] = super_df.apply(format_game_time, axis=1)
        super_df = super_df.rename(columns={'AWAY': 'Away', 'HOME': 'Home', 'All_Players': 'Players'})
        super_display = super_df[['Away', 'Home', 'Game Time (ET)', 'TV', 'Players']]

        st.dataframe(
            super_display,
            hide_index=True,
            height=300,
            column_config={
                "Away": st.column_config.TextColumn("Away", width=120),
                "Home": st.column_config.TextColumn("Home", width=120),
                "Game Time (ET)": st.column_config.TextColumn("Game Time (ET)", width=110),
                "TV": st.column_config.TextColumn("TV", width=60),
                "Players": st.column_config.TextColumn("Players", width=300)
            }
        )
    else:
        st.info("No super matchups found")

# TAB 3: Games by Date
with tab3:
    st.header("Games by Date")
    st.caption("Browse games by date with prospects playing.")

    if not games_with_players.empty:
        today = get_eastern_today()
        date_options = sorted(games_with_players['DATE'].dropna().unique())

        if date_options:
            unique_games = games_with_players.drop_duplicates(subset=['DATE', 'AWAY', 'HOME'])
            game_counts = unique_games.groupby('DATE').size().to_dict()

            col_date, col_count = st.columns([1, 2])

            with col_date:
                selected_date = st.date_input(
                    "Select Date",
                    value=today if today in date_options else date_options[0],
                    min_value=date_options[0],
                    max_value=date_options[-1],
                    label_visibility="collapsed"
                )

            filtered_games = unique_games[unique_games['DATE'] == selected_date]

            with col_count:
                if not filtered_games.empty:
                    game_count = game_counts.get(selected_date, 0)
                    st.markdown(f"### {game_count} game{'s' if game_count != 1 else ''} on {selected_date.strftime('%a, %b %d, %Y')}")

            if not filtered_games.empty:
                filtered_df = filtered_games.copy()
                filtered_df['Game Time (ET)'] = filtered_df.apply(format_game_time, axis=1)
                filtered_df = filtered_df.rename(columns={'AWAY': 'Away', 'HOME': 'Home', 'All_Players': 'Players'})
                filtered_display = filtered_df[['Away', 'Home', 'Game Time (ET)', 'TV', 'Players']]

                st.dataframe(
                    filtered_display,
                    hide_index=True,
                    height=350,
                    column_config={
                        "Away": st.column_config.TextColumn("Away", width=120),
                        "Home": st.column_config.TextColumn("Home", width=120),
                        "Game Time (ET)": st.column_config.TextColumn("Game Time (ET)", width=110),
                        "TV": st.column_config.TextColumn("TV", width=60),
                        "Players": st.column_config.TextColumn("Players", width=250)
                    }
                )
            else:
                st.info(f"No games scheduled for {selected_date.strftime('%A, %B %d, %Y')}")
    else:
        st.info("No schedule data available")

# TAB 4: Prospect Distribution
with tab4:
    st.header("Prospect Distribution")
    st.caption("Number of NBA prospects by school/country.")

    if not draft_df.empty:
        school_summary = draft_df.groupby(['School'])['Player'].count()
        top_schools = school_summary.nlargest(15)

        fig, ax = plt.subplots(figsize=(6, 10))

        colors = plt.cm.Blues(np.linspace(0.5, 0.9, len(top_schools)))
        bars = ax.barh(range(len(top_schools)), top_schools.values, color=colors)

        ax.set_yticks(range(len(top_schools)))
        ax.set_yticklabels(top_schools.index)
        ax.invert_yaxis()

        for i, (bar, value) in enumerate(zip(bars, top_schools.values)):
            ax.text(
                bar.get_width() - 0.1,
                bar.get_y() + bar.get_height() / 2,
                str(value),
                ha='right',
                va='center',
                color='white',
                fontsize=11,
                fontweight='bold'
            )

        ax.set_xlabel("Number of NBA Prospects", fontsize=12)
        ax.set_ylabel("School/Country", fontsize=12)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis='x', alpha=0.2, linestyle='--')

        st.pyplot(fig)
    else:
        st.info("No draft data available")

# Footer
st.divider()
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Sources")
    st.write("[NBA Draft Mock Board](https://www.nbadraft.net/nba-mock-drafts/?year-mock=2026)")
    date_str = (get_eastern_today() + timedelta(days=1)).strftime("%Y%m%d")
    st.write(f"[ESPN NCAA Schedule](https://www.espn.com/mens-college-basketball/schedule/_/date/{date_str})")
    st.caption(f"Eastern Time: {get_eastern_now().strftime('%I:%M %p ET')}")

with col2:
    st.text("")

with col3:
    st.caption("Data refreshes every 2 hours")
