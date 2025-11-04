import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from tabulate import tabulate as tab
import json
import os

# File paths for loading data
DATA_DIR = "data"
DRAFT_DATA_FILE = os.path.join(DATA_DIR, "draft_data.csv")
SCHEDULE_DATA_FILE = os.path.join(DATA_DIR, "schedule_data.csv")
SCRAPE_METADATA_FILE = os.path.join(DATA_DIR, "scrape_metadata.json")

# Helper functions for Eastern timezone
def get_eastern_now():
    """Get current datetime in Eastern timezone"""
    return datetime.now(ZoneInfo("America/New_York"))

def get_eastern_today():
    """Get today's date in Eastern timezone"""
    return get_eastern_now().date()


# =================================================================== Load Data from Files

def get_file_mtime(filepath):
    """Get file modification time for cache invalidation"""
    if os.path.exists(filepath):
        return os.path.getmtime(filepath)
    return 0

@st.cache_data(ttl=3600)  # 1 hour TTL for draft data
def load_draft_data(file_mtime):
    """Load draft board data from CSV file
    
    Args:
        file_mtime: File modification time (used to invalidate cache when file updates)
    """
    if os.path.exists(DRAFT_DATA_FILE):
        return pd.read_csv(DRAFT_DATA_FILE)
    else:
        st.error(f"Draft data file not found. Please run `python scraper.py` to generate data.")
        return pd.DataFrame()

@st.cache_data(ttl=1800)  # 30 minutes TTL for today's games
def load_todays_schedule(file_mtime, today):
    """Load today's schedule with frequent refresh
    
    Args:
        file_mtime: File modification time
        today: Today's date for cache key
    """
    if os.path.exists(SCHEDULE_DATA_FILE):
        df = pd.read_csv(SCHEDULE_DATA_FILE)
        if not df.empty:
            df['DATE'] = pd.to_datetime(df['DATE']).dt.date
            return df[df['DATE'] == today]
        return pd.DataFrame()
    else:
        return pd.DataFrame()

@st.cache_data(ttl=43200)  # 12 hours TTL for near-future games
def load_nearfuture_schedule(file_mtime, date_range_key):
    """Load next 7 days schedule with moderate refresh
    
    Args:
        file_mtime: File modification time
        date_range_key: Date range identifier for cache key
    """
    if os.path.exists(SCHEDULE_DATA_FILE):
        df = pd.read_csv(SCHEDULE_DATA_FILE)
        if not df.empty:
            df['DATE'] = pd.to_datetime(df['DATE']).dt.date
            today = get_eastern_today()
            tomorrow = today + timedelta(days=1)
            week_end = today + timedelta(days=7)
            return df[(df['DATE'] >= tomorrow) & (df['DATE'] <= week_end)]
        return pd.DataFrame()
    else:
        return pd.DataFrame()

@st.cache_data(ttl=86400)  # 24 hours TTL for far-future games
def load_farfuture_schedule(file_mtime, date_range_key):
    """Load 8-30 days schedule with infrequent refresh
    
    Args:
        file_mtime: File modification time
        date_range_key: Date range identifier for cache key
    """
    if os.path.exists(SCHEDULE_DATA_FILE):
        df = pd.read_csv(SCHEDULE_DATA_FILE)
        if not df.empty:
            df['DATE'] = pd.to_datetime(df['DATE']).dt.date
            today = get_eastern_today()
            week_start = today + timedelta(days=8)
            month_end = today + timedelta(days=30)
            return df[(df['DATE'] >= week_start) & (df['DATE'] <= month_end)]
        return pd.DataFrame()
    else:
        return pd.DataFrame()

def load_schedule_data_smart():
    """Load schedule data with tiered caching strategy
    
    Returns combined DataFrame with different TTLs for different date ranges:
    - Today's games: 30 min refresh
    - Next 7 days: 12 hour refresh  
    - 8-30 days out: 24 hour refresh
    """
    file_mtime = get_file_mtime(SCHEDULE_DATA_FILE)
    today = get_eastern_today()
    
    # Load data with different cache TTLs
    todays_games = load_todays_schedule(file_mtime, today)
    nearfuture_games = load_nearfuture_schedule(file_mtime, today.strftime("%Y-%m-%d"))
    farfuture_games = load_farfuture_schedule(file_mtime, today.strftime("%Y-%m-%d"))
    
    # Combine all DataFrames
    combined = pd.concat([todays_games, nearfuture_games, farfuture_games], ignore_index=True)
    
    if combined.empty:
        st.error(f"Schedule data file not found. Please run `python scraper.py` to generate data.")
    
    return combined

def load_metadata():
    """Load scrape metadata"""
    if os.path.exists(SCRAPE_METADATA_FILE):
        with open(SCRAPE_METADATA_FILE, 'r') as f:
            return json.load(f)
    return None

# Load data with smart tiered caching
draft_df = load_draft_data(get_file_mtime(DRAFT_DATA_FILE))
combined_df = load_schedule_data_smart()
metadata = load_metadata()

# Exit early if data is missing
if draft_df.empty or combined_df.empty:
    st.stop()

# =================================================================== Clean Draft Data

# Convert Draft Rank to Int for Sorting purposes
draft_df["Rank"] = draft_df["Rank"].astype(int)

# Clean Draft Board Schools
# Create duplicate column for cleaning and merging
draft_df['School_Merge'] = draft_df['School']
draft_df['School_Merge'] = draft_df['School_Merge'].str.replace(r'St\.$', 'State', regex=True)
draft_df['School_Merge'] = draft_df['School_Merge'].str.replace(r'^St\.', 'Saint', regex=True)
draft_df['School_Merge'] = draft_df['School_Merge'].str.replace("'", "")

# =================================================================== Clean Schedule Data

# Note: Column renaming is now done in scraper.py before saving
# Columns are: AWAY, HOME, TIME, TV, TICKETS, LOCATION, ODDS_BY, DATE

# Create duplicate df to join on home or away team.
combined_df_home = combined_df.copy()
combined_df_away = combined_df.copy()

# Clean team names in schedule
combined_df_home['TEAM'] = combined_df_home['HOME'].str.replace(r'[@0-9]', '', regex=True).str.strip()
combined_df_away['TEAM'] = combined_df_away['AWAY'].str.replace(r'[@0-9]', '', regex=True).str.strip()

# Concatenate home and away df
combined_df = pd.concat([combined_df_home, combined_df_away])

combined_df['TEAM'] = combined_df['TEAM'].str.replace("'", "")
combined_df['TEAM'] = combined_df['TEAM'].str.replace(r'St\.$', 'State', regex=True)
combined_df['TEAM'] = combined_df['TEAM'].str.replace(r'^St\.', 'Saint', regex=True)

combined_df['HomeTeam'] = combined_df['HOME'].str.replace(r'[@0-9]', '', regex=True).str.strip()
combined_df['HomeTeam'] = combined_df['HomeTeam'].str.replace(r'St\.$', 'State', regex=True)
combined_df['HomeTeam'] = combined_df['HomeTeam'].str.replace(r'^St\.', 'Saint', regex=True)
combined_df['HomeTeam'] = combined_df['HomeTeam'].str.replace("'", "")

combined_df['AwayTeam'] = combined_df['AWAY'].str.replace(r'[@0-9]', '', regex=True).str.strip()
combined_df['AwayTeam'] = combined_df['AwayTeam'].str.replace(r'St\.$', 'State', regex=True)
combined_df['AwayTeam'] = combined_df['AwayTeam'].str.replace(r'^St\.', 'Saint', regex=True)
combined_df['AwayTeam'] = combined_df['AwayTeam'].str.replace("'", "")


# ==================================================================================== Add column for Players In Games

# Function to get players from a given school
def get_players_from_school(school):
    players = draft_df[draft_df['School_Merge'] == school][['Rank', 'Player', 'School']]
    return players.to_dict(orient='records')


# Apply get_players_from_school to HomeTeam and AwayTeam
combined_df['HomeTeam_Players'] = combined_df['HomeTeam'].apply(get_players_from_school)
combined_df['AwayTeam_Players'] = combined_df['AwayTeam'].apply(get_players_from_school)

# Combine home and away players into a single list
combined_df['All_Players'] = combined_df.apply(
    lambda row: row['HomeTeam_Players'] + row['AwayTeam_Players'], axis=1
)

# Sort players by rank before formatting
combined_df['All_Players'] = combined_df.apply(
    lambda row: ', '.join([
        f"{p['School']}-#{str(p['Rank'])} {p['Player']}"
        for p in sorted(row['All_Players'], key=lambda x: int(x['Rank']))
    ]),
    axis=1
)

# ==================================================================================== Prepare Tables for Display

# Merge draft board with upcoming games
upcoming_games_df = combined_df[combined_df['TEAM'].isin(draft_df['School_Merge'])]
draft_with_games = pd.merge(draft_df, upcoming_games_df, left_on='School_Merge', right_on='TEAM', how='left')

draft_with_games = draft_with_games[
    ['Rank', 'Team', 'Player', 'School', 'DATE', 'TIME', 'TV', 'AWAY', 'HOME', 'HomeTeam', 'AwayTeam']]

# Highlight matchups with NBA prospects on both teams
super_matchups = combined_df[
    (combined_df['HomeTeam'].isin(draft_df['School_Merge'])) & (combined_df['AwayTeam'].isin(draft_df['School_Merge']))]

super_matchups = super_matchups[
    ['AWAY', 'HOME', 'DATE', 'TIME', 'TV', 'HomeTeam', 'AwayTeam', 'All_Players']].drop_duplicates()

# Merge super_matchups with draft data to get players for each game
super_matchups_expanded = super_matchups.copy()

# Super Matchups: Drop unnecessary columns and keep only the relevant details
super_matchups_expanded = super_matchups_expanded[['AWAY', 'HOME', 'DATE', 'TIME', 'TV', 'All_Players']]

# Sort by Rank (ascending) and then by Date
draft_with_games = draft_with_games.sort_values(by=['Rank', 'DATE'], ascending=[True, True])

draft_with_games = draft_with_games.reset_index(drop=True)

# Draft Board: Drop unnecessary columns and keep only the relevant details
draft_with_games = draft_with_games[['Rank', 'Team', 'Player', 'School', 'DATE', 'TIME', 'TV', 'AWAY', 'HOME']]

# Drop dupes
draft_with_games = draft_with_games.drop_duplicates(subset=['Rank', 'Player', 'School'])

# =================================================================== Add NBA Team Logos
# NBA team name to logo URL mapping (using ESPN's CDN)
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

# Function to get team logo URL, handling asterisks and variations
def get_team_logo(team_name):
    """Get logo URL for a team, stripping asterisks and handling variations"""
    if pd.isna(team_name) or team_name == "":
        return ""
    # Remove asterisks (used for projected picks)
    clean_name = team_name.strip().replace("*", "")
    return NBA_TEAM_LOGOS.get(clean_name, "")

# Replace team names with logo URLs
draft_with_games['Team'] = draft_with_games['Team'].apply(get_team_logo)

# ==================================================================================== Format Game Time (ET) Column
# Helper function to format date and time
def format_game_time(row):
    """Format DATE and TIME into 'Nov 8, 9:00 PM' format"""
    if pd.isna(row['DATE']) or pd.isna(row['TIME']):
        return ""
    try:
        date_obj = row['DATE'] if isinstance(row['DATE'], date) else pd.to_datetime(row['DATE']).date()
        month_day = date_obj.strftime('%b %-d')  # e.g., "Nov 8"
        time_str = str(row['TIME']).strip()
        return f"{month_day}, {time_str}" if time_str else month_day
    except:
        return ""

# Create formatted Game Time column for draft board
draft_with_games['Game Time (ET)'] = draft_with_games.apply(format_game_time, axis=1)

# Create formatted Game Time column for super matchups
super_matchups_expanded['Game Time (ET)'] = super_matchups_expanded.apply(format_game_time, axis=1)

# ==================================================================================== Fragment Definition
# Fragment for Games by Date tab to prevent full app reruns on date changes
@st.fragment
def games_by_date_fragment(combined_df, upcoming_games_df):
    """Fragment that handles date selection and displays games for selected date.
    
    Only this fragment reruns when the date changes, not the entire app.
    """
    # Get date range for calendar
    today = get_eastern_today()
    date_options = sorted(combined_df['DATE'].dropna().unique())
    
    # Handle empty date options gracefully
    if not date_options:
        st.warning("No schedule data available. Please run `python scraper.py` to generate data.")
    else:
        # Deduplicate games (remove duplicate rows for games with prospects on both teams)
        unique_games = upcoming_games_df.drop_duplicates(subset=['DATE', 'AWAY', 'HOME'])
        
        # Calculate game counts for each date using unique matchups
        game_counts = unique_games.groupby('DATE').size().to_dict()
        
        min_cal_date = date_options[0]
        max_cal_date = date_options[-1]
        
        # Initialize session state for selected date
        if 'selected_date' not in st.session_state:
            st.session_state['selected_date'] = today if today in date_options else date_options[0]
        
        # Safety check: reset selected date if it falls outside available range
        if st.session_state['selected_date'] not in date_options:
            st.session_state['selected_date'] = today if today in date_options else date_options[0]
        
        # Date picker and game count on same line
        col_date, col_count = st.columns([1, 2])
        
        with col_date:
            selected_date = st.date_input(
                "Select Date",
                value=st.session_state['selected_date'],
                min_value=min_cal_date,
                max_value=max_cal_date,
                label_visibility="collapsed"
            )
        
        # Update session state
        st.session_state['selected_date'] = selected_date
        
        # Filter unique games for the selected date (deduplicated)
        filtered_games = unique_games[unique_games['DATE'] == selected_date]
        
        # Display game count in the right column
        with col_count:
            if not filtered_games.empty:
                game_count = game_counts.get(selected_date, 0)
                st.markdown(f"""
                <div style="margin-top: -0.5rem;">
                    <h3 style="margin-top: 0; margin-bottom: 0;">{game_count} game{'s' if game_count != 1 else ''} on {selected_date.strftime('%a, %b %d, %Y')}</h3>
                </div>
                """, unsafe_allow_html=True)
        
        if not filtered_games.empty:
            
            # Merge filtered games with draft data to add player info
            filtered_games_expanded = filtered_games.copy()
            
            # Format game time for filtered games
            filtered_games_expanded['Game Time (ET)'] = filtered_games_expanded.apply(format_game_time, axis=1)
        
            # Drop unnecessary columns and keep only relevant details
            filtered_df = filtered_games_expanded.copy()
            filtered_df = filtered_df.rename(columns={'AWAY': 'Away', 'HOME': 'Home', 'All_Players': 'Players'})
            filtered_games_display = filtered_df[['Away', 'Home', 'Game Time (ET)', 'TV', 'Players']]
        
            # Display in Streamlit
            st.dataframe(filtered_games_display, hide_index=True, height=350, use_container_width=True)
        else:
            st.info(f"No games scheduled for {selected_date.strftime('%A, %B %d, %Y')}")

# ==================================================================================== Create Streamlit Display
# Streamlit App

st.set_page_config(layout="wide")

# Add custom CSS for modern, cohesive design
st.markdown("""
<style>
    /* ===== Color Palette ===== */
    :root {
        --primary-blue: #3b82f6;
        --primary-dark: #2563eb;
        --primary-light: #60a5fa;
        --accent: #8b5cf6;
        --bg-light: #f8fafc;
        --bg-card: #ffffff;
        --border-color: #e2e8f0;
        --text-primary: #1e293b;
        --text-secondary: #64748b;
        --hover-bg: #f1f5f9;
        --table-even-row: #f8fafc;
        --table-hover: #e0f2fe;
    }
    
    /* ===== Layout & Spacing ===== */
    .main .block-container {
        padding-top: 0.1rem;
        padding-bottom: 1rem;
        max-width: 1400px;
        margin: 0 auto;
    }
    
    hr {
        margin-top: 0.25rem;
        margin-bottom: 0.75rem;
        border: none;
        border-top: 1px solid var(--border-color);
    }
    
    h1 {
        margin-top: 0 !important;
        margin-bottom: 0.25rem !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }
    
    /* ===== Tabs Styling ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 60px;
        padding: 0px 24px;
        background-color: var(--bg-light);
        border: 1px solid var(--border-color);
        border-radius: 8px 8px 0px 0px;
        font-size: 16px;
        font-weight: 600;
        color: var(--text-secondary);
        transition: all 0.2s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: var(--hover-bg);
        border-color: var(--primary-light);
        color: var(--text-primary);
        transform: translateY(-2px);
    }
    
    .stTabs [aria-selected="true"] {
        background-color: var(--primary-blue) !important;
        border-color: var(--primary-blue) !important;
        color: white !important;
        box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.2);
    }
    
    /* ===== DataFrames & Tables ===== */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
    }
    
    /* Table header styling */
    .stDataFrame thead tr th {
        background-color: var(--primary-blue) !important;
        color: white !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 12px 8px !important;
        border: none !important;
        position: sticky !important;
        top: 0 !important;
        z-index: 10 !important;
    }
    
    /* Table body styling */
    .stDataFrame tbody tr:nth-child(even) {
        background-color: var(--table-even-row) !important;
    }
    
    .stDataFrame tbody tr:hover {
        background-color: var(--table-hover) !important;
        transition: background-color 0.15s ease;
    }
    
    .stDataFrame tbody tr td {
        border-bottom: 1px solid var(--border-color) !important;
        padding: 10px 8px !important;
        font-size: 14px !important;
    }
    
    /* ===== Cards & Containers ===== */
    .element-container {
        transition: all 0.2s ease;
    }
    
    /* ===== Headers ===== */
    h2, h3 {
        color: var(--text-primary) !important;
        font-weight: 600 !important;
    }
    
    /* ===== Buttons ===== */
    .stButton button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease;
        border: 1px solid var(--border-color);
    }
    
    .stButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border-color: var(--primary-blue);
    }
    
    /* ===== Date Input ===== */
    .stDateInput input {
        border-radius: 8px;
        border: 1px solid var(--border-color);
        transition: all 0.2s ease;
    }
    
    .stDateInput input:focus {
        border-color: var(--primary-blue);
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    
    /* ===== Info Boxes ===== */
    .stAlert {
        border-radius: 8px;
        border-left: 4px solid var(--primary-blue);
    }
    
    /* ===== Popover ===== */
    [data-baseweb="popover"] {
        border-radius: 12px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border: 1px solid var(--border-color);
    }
    
    /* ===== Loading Spinner ===== */
    .stSpinner > div {
        border-top-color: var(--primary-blue) !important;
    }
    
    /* ===== Text Styling ===== */
    .stMarkdown p {
        color: var(--text-primary);
    }
    
    .stCaption {
        color: var(--text-secondary) !important;
    }
</style>
""", unsafe_allow_html=True)

# Header with info popover
col_title, col_info = st.columns([9, 1])
with col_title:
    st.title("NBA Prospect Schedule")
with col_info:
    with st.popover("ℹ️"):
        st.markdown("**About**")
        st.caption("This page helps basketball fans keep track of upcoming NCAA games featuring "
                "top prospects for the 2026 NBA Draft. If you don't follow college basketball "
                "but want to know when the next potential NBA stars are playing, this is your "
                "go-to schedule. Check back for updates on key matchups and players to watch.")
        
        # Show data info with metadata
        if metadata:
            st.markdown("**Data Info**")
            last_scrape = datetime.fromisoformat(metadata['last_scrape_time'])
            st.caption(f"📅 Source data from: {last_scrape.strftime('%b %d, %Y at %I:%M %p ET')}")
            st.caption(f"Draft prospects: {metadata.get('draft_prospects_count', 'N/A')}")
            st.caption(f"Games: {metadata.get('games_count', 'N/A')}")
            
            st.markdown("**Smart Refresh**")
            st.caption("🔄 Today's games refresh every 30 min")
            st.caption("🔄 Next 7 days refresh every 12 hours")
            st.caption("🔄 Future games refresh daily")
            
            if st.button("🔄 Force Refresh", help="Clear all caches and reload immediately"):
                st.cache_data.clear()
                st.rerun()

st.divider()

# Create tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["📋 Draft Board", "⭐ Super Matchups", "📅 Games by Date", "📊 Prospect Distribution"])

with tab1:
    st.header("Draft Board with Next Games")
    st.caption("Top 60 prospects ranked with their next scheduled game.")
    
    # Select columns to display (use Game Time instead of separate DATE and TIME)
    display_df = draft_with_games.copy()
    display_df = display_df.rename(columns={'AWAY': 'Away', 'HOME': 'Home'})
    draft_display = display_df[['Rank', 'Team', 'Player', 'School', 'Game Time (ET)', 'TV', 'Away', 'Home']]
    
    st.dataframe(
        draft_display, 
        hide_index=True, 
        height=400, 
        use_container_width=True,
        column_config={
            "Team": st.column_config.ImageColumn(
                "Team",
                help="NBA Team Logo",
                width="small"
            ),
            "Rank": st.column_config.NumberColumn(
                "Rank",
                help="Mock draft ranking (consensus)",
                width="small"
            ),
            "Player": st.column_config.TextColumn(
                "Player",
                help="Player name",
                width="medium"
            ),
            "School": st.column_config.TextColumn(
                "School",
                help="College or country",
                width="medium"
            )
        }
    )

with tab2:
    st.header("Super Matchups")
    st.caption("Games featuring prospects on both teams.")
    
    # Select columns to display
    super_df = super_matchups_expanded.copy()
    super_df = super_df.rename(columns={'AWAY': 'Away', 'HOME': 'Home', 'All_Players': 'Players'})
    super_display = super_df[['Away', 'Home', 'Game Time (ET)', 'TV', 'Players']]
    
    st.dataframe(super_display, hide_index=True, height=300, use_container_width=True)

with tab3:
    st.header("Games by Date")
    st.caption("Browse games by date for the next 30 days.")
    
    # Call the fragment (defined at module scope to avoid redecorating on every rerun)
    games_by_date_fragment(combined_df, upcoming_games_df)

with tab4:
    st.header("NBA Prospect Distribution by School/Country")
    st.caption("Which schools produce the most NBA prospects.")
    
    # ==================================================================================== Chart
    
    school_summary = draft_df.groupby(['School'])['Player'].count()
    school_summary = school_summary.reset_index()
    school_summary = school_summary.rename(columns={'School': 'School/Country', 'Player': 'Total'})
    school_summary = school_summary.sort_values(by='Total', ascending=False)
    
    # Create a figure and axis with increased height to prevent overlap
    fig, ax = plt.subplots(figsize=(8, 12))
    
    # Set colors
    fig.patch.set_facecolor('white')
    ax.set_facecolor('#f8fafc')
    colors_list = ['#93c5fd', '#60a5fa', '#3b82f6', '#2563eb', '#1d4ed8']
    text_color = '#1e293b'
    tick_color = '#64748b'
    border_color = '#e2e8f0'

    # Create a modern blue gradient color palette
    from matplotlib.colors import LinearSegmentedColormap
    n_bins = len(school_summary)
    cmap = LinearSegmentedColormap.from_list('blue_gradient', colors_list, N=n_bins)
    
    values = np.array(school_summary['Total'])
    norm = plt.Normalize(values.min(), values.max())
    colors = [cmap(norm(value)) for value in values]
    
    # Create a bar plot of Schools with the most prospects
    bars = sns.barplot(
        data=school_summary,
        x="Total",
        y="School/Country",
        hue="School/Country",
        ax=ax,
        palette=colors,
        legend=False,
        edgecolor=border_color,
        linewidth=1
    )
    
    # Add value labels inside the bars in white
    for i, (value, bar) in enumerate(zip(school_summary['Total'], ax.patches)):
        ax.text(
            bar.get_width() - 0.2,
            bar.get_y() + bar.get_height() / 2,
            str(value),
            ha='right',
            va='center',
            color='white',
            fontsize=11,
            fontweight='bold'
        )
    
    # Set labels and title with modern styling
    ax.set_xlabel("Number of NBA Prospects", fontsize=12, fontweight='600', color=text_color)
    ax.set_ylabel("School/Country", fontsize=12, fontweight='600', color=text_color)
    
    # Style the spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(border_color)
    ax.spines['bottom'].set_color(border_color)
    
    # Style the ticks
    ax.tick_params(colors=tick_color, labelsize=10)
    ax.set_xticks([0, 1, 2, 3])
    
    # Add subtle grid
    ax.grid(axis='x', alpha=0.2, linestyle='--', linewidth=0.5, color=tick_color)
    
    # Display the plot in Streamlit
    st.pyplot(fig)

st.divider()
# ==================================================================================== Footer
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Sources")
    url = "https://www.nbadraft.net/nba-mock-drafts/?year-mock=2026"
    st.write("[NBA Draft Mock Board](%s)" % url)
    single_date = get_eastern_today() + timedelta(days=1)  # Start with tomorrow (Eastern time)
    date_str = single_date.strftime("%Y%m%d")
    url = f"https://www.espn.com/mens-college-basketball/schedule/_/date/{date_str}"
    st.write("[ESPN NCAA Schedule](%s)" % url)
    url = "https://www.jstew.info"
    st.write("[Created by jstew.info](%s)" % url)
    
    # Show current Eastern time for reference
    eastern_time = get_eastern_now()
    st.caption(f"Eastern Time: {eastern_time.strftime('%I:%M %p ET')}")

with col2:
    st.text("")

with col3:
    st.markdown(
        '<a href="https://www.jstew.info/" target="_blank">'
        '<img src="app/static/logo.png" width="200">'
        '</a>',
        unsafe_allow_html=True
    )
