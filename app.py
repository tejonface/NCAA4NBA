import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from tabulate import tabulate as tab
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# Helper functions for Eastern timezone
def get_eastern_now():
    """Get current datetime in Eastern timezone"""
    return datetime.now(ZoneInfo("America/New_York"))

def get_eastern_today():
    """Get today's date in Eastern timezone"""
    return get_eastern_now().date()



# =================================================================== Scrape NBA Draft Board
# Function to scrape NBA draft board tables
@st.cache_data(ttl=1800)
def scrape_nba_mock_draft(url):
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
    return df


# Scrape draft data
draft_url = "https://www.nbadraft.net/nba-mock-drafts/?year-mock=2026"
draft_df = scrape_nba_mock_draft(draft_url)



# =================================================================== Scrape NCAA Schedule

# File paths for caching
CACHE_DIR = "schedule_cache"
CACHE_FILE = os.path.join(CACHE_DIR, "ncaa_schedule.json")
CACHE_METADATA_FILE = os.path.join(CACHE_DIR, "metadata.json")

# Create cache directory if it doesn't exist
os.makedirs(CACHE_DIR, exist_ok=True)

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

# Load cached data
def load_cache():
    """Load cached schedule data from file"""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}

# Save cache data
def save_cache(cache_data, dates_scraped=None):
    """Save schedule data to cache file"""
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache_data, f)
    
    # Load existing metadata to preserve per-date timestamps
    if os.path.exists(CACHE_METADATA_FILE):
        with open(CACHE_METADATA_FILE, 'r') as f:
            metadata = json.load(f)
        # Migrate from old format if needed
        if 'date_timestamps' not in metadata:
            metadata['date_timestamps'] = {}
    else:
        metadata = {'date_timestamps': {}}
    
    # Update timestamps for newly scraped dates
    if dates_scraped:
        for date_str in dates_scraped:
            metadata['date_timestamps'][date_str] = get_eastern_now().isoformat()
    
    # Keep track of all cached dates
    metadata['dates_cached'] = list(cache_data.keys())
    
    with open(CACHE_METADATA_FILE, 'w') as f:
        json.dump(metadata, f)

# Check if date needs refresh with tiered intervals
def needs_refresh(date_str, cache_metadata):
    """Check if a specific date's data needs refreshing"""
    if not os.path.exists(CACHE_METADATA_FILE):
        return True
    
    # Tiered refresh intervals based on how far out the game is:
    # - Within 7 days: refresh every 30 minutes (games happening soon)
    # - 7-30 days: refresh every 12 hours (schedules more stable)
    # - 30+ days: refresh every 24 hours (minimal changes)
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    days_diff = (target_date - get_eastern_today()).days
    
    if days_diff < 7:
        max_age = timedelta(minutes=30)
    elif days_diff < 30:
        max_age = timedelta(hours=12)
    else:
        max_age = timedelta(hours=24)
    
    # Check per-date timestamp from metadata
    if cache_metadata and 'date_timestamps' in cache_metadata:
        date_timestamps = cache_metadata['date_timestamps']
        if date_str in date_timestamps:
            last_update = datetime.fromisoformat(date_timestamps[date_str])
            # Make last_update timezone-aware if it's not
            if last_update.tzinfo is None:
                last_update = last_update.replace(tzinfo=ZoneInfo("America/New_York"))
            return get_eastern_now() - last_update > max_age
    
    return True

# Main function to get NCAA schedule with caching and parallel scraping
@st.cache_data(ttl=1800)  # 30-minute Streamlit cache on top of file cache
def scrape_ncaa_schedule():
    """Scrape NCAA schedule with file caching and parallel processing"""
    cache_data = load_cache()
    
    # Load metadata
    if os.path.exists(CACHE_METADATA_FILE):
        with open(CACHE_METADATA_FILE, 'r') as f:
            cache_metadata = json.load(f)
    else:
        cache_metadata = {}
    
    # Determine which dates to scrape
    dates_to_scrape = []
    for i in range(150):
        single_date = get_eastern_today() + timedelta(days=i)
        date_str = single_date.strftime("%Y-%m-%d")
        
        # Check if we need to refresh this date
        if date_str not in cache_data or needs_refresh(date_str, cache_metadata):
            dates_to_scrape.append(single_date)
    
    # Scrape missing dates in parallel
    if dates_to_scrape:
        print(f"Scraping {len(dates_to_scrape)} dates in parallel...")
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_date = {executor.submit(scrape_single_date, d): d for d in dates_to_scrape}
            
            for future in as_completed(future_to_date):
                single_date = future_to_date[future]
                try:
                    result = future.result()
                    if result:
                        date_str = single_date.strftime("%Y-%m-%d")
                        cache_data[date_str] = result
                        print(f"Scraped {date_str}")
                except Exception as e:
                    print(f"Error processing {single_date}: {e}")
        
        # Save updated cache with newly scraped dates
        scraped_date_strs = [d.strftime("%Y-%m-%d") for d in dates_to_scrape]
        save_cache(cache_data, scraped_date_strs)
    
    # Convert cached data to DataFrame
    all_records = []
    for date_str in sorted(cache_data.keys()):
        all_records.extend(cache_data[date_str])
    
    combined_df = pd.DataFrame(all_records)
    if not combined_df.empty:
        combined_df['DATE'] = pd.to_datetime(combined_df['DATE']).dt.date
    
    return combined_df

# Scrape NCAA schedule
combined_df = scrape_ncaa_schedule()

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

# Rename schedule columns
# ESPN's current structure: MATCHUP, '', TIME, TV, tickets, location, logo espnbet, DATE
combined_df = combined_df.rename(columns={
    'MATCHUP': 'AWAY',
    '': 'HOME',
    'tickets': 'TICKETS',
    'location': 'LOCATION',
    'logo espnbet': 'ODDS_BY'
})

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
print(tab(combined_df.head(),headers="firstrow", tablefmt="grid"))
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

# print(tabulate(super_matchups, headers='keys', tablefmt='psql'))
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

# ==================================================================================== Create Streamlit Display
# Streamlit App

st.set_page_config(layout="centered")

# Add custom CSS for larger, styled tabs and tighter spacing
st.markdown("""
<style>
    /* Reduce whitespace around title */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 1rem;
    }
    
    /* Reduce spacing around dividers */
    hr {
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }
    
    /* Make tabs larger with better spacing */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 60px;
        padding: 0px 24px;
        background-color: #f0f2f6;
        border-radius: 8px 8px 0px 0px;
        font-size: 18px;
        font-weight: 600;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #e0e3e9;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #4CAF50 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# Header with info popover
col_title, col_info = st.columns([10, 1])
with col_title:
    st.title("NBA Prospect Schedule")
with col_info:
    with st.popover("ℹ️"):
        st.markdown("### About")
        st.text("This page helps basketball fans keep track of upcoming NCAA games featuring "
                "top prospects for the 2026 NBA Draft. If you don't follow college basketball "
                "but want to know when the next potential NBA stars are playing, this is your "
                "go-to schedule. Check back for updates on key matchups and players to watch.")
        
        st.divider()
        
        # Show data info with refresh button
        min_date = combined_df['DATE'].min() if not combined_df.empty else None
        max_date = combined_df['DATE'].max() if not combined_df.empty else None
        if min_date and max_date:
            st.markdown("### Data Info")
            st.info(f"📅 Showing games from {min_date.strftime('%b %d, %Y')} to {max_date.strftime('%b %d, %Y')}")
            st.caption("Data refreshes: 30min (next week), 12hr (next month), 24hr (beyond)")
            
            if st.button("🔄 Refresh Data", help="Clear cache and reload latest games"):
                st.cache_data.clear()
                st.rerun()

st.divider()

# Create tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["📋 Draft Board", "⭐ Super Matchups", "📅 Games by Date", "📊 Prospect Distribution"])

with tab1:
    st.header("Draft Board with Next Games")
    st.text("2026 NBA Mock Draft board with each NCAA player's upcoming game.")
    
    # Select columns to display (use Game Time instead of separate DATE and TIME)
    draft_display = draft_with_games[['Rank', 'Team', 'Player', 'School', 'Game Time (ET)', 'TV', 'AWAY', 'HOME']]
    
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
            )
        }
    )
    print(tab(draft_with_games))

with tab2:
    st.header("SUPER MATCHUPS")
    st.text("Games with top 60 NBA draft prospects on both teams.")
    
    # Select columns to display
    super_display = super_matchups_expanded[['AWAY', 'HOME', 'Game Time (ET)', 'TV', 'All_Players']]
    
    st.dataframe(super_display, hide_index=True, height=300, use_container_width=True)
    print(tab(super_matchups_expanded))

with tab3:
    st.header("Games by Date")
    
    # Get date range for calendar
    today = get_eastern_today()
    date_options = sorted(combined_df['DATE'].dropna().unique())
    
    # Handle empty date options gracefully
    if not date_options:
        st.warning("No schedule data available. Please try refreshing the data.")
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
        
        # Calendar date picker
        selected_date = st.date_input(
            "Select date",
            value=st.session_state['selected_date'],
            min_value=min_cal_date,
            max_value=max_cal_date
        )
        
        # Update session state
        st.session_state['selected_date'] = selected_date
        
        # Filter unique games for the selected date (deduplicated)
        filtered_games = unique_games[unique_games['DATE'] == selected_date]
        
        if not filtered_games.empty:
            game_count = game_counts.get(selected_date, 0)
            st.write(f"**{game_count} game{'s' if game_count != 1 else ''} on {selected_date.strftime('%A, %B %d, %Y')}**")
            
            # Merge filtered games with draft data to add player info
            filtered_games_expanded = filtered_games.copy()
            
            # Format game time for filtered games
            filtered_games_expanded['Game Time (ET)'] = filtered_games_expanded.apply(format_game_time, axis=1)
        
            # Drop unnecessary columns and keep only relevant details
            filtered_games_display = filtered_games_expanded[['AWAY', 'HOME', 'Game Time (ET)', 'TV', 'All_Players']]
        
            # Display in Streamlit
            st.dataframe(filtered_games_display, hide_index=True, height=350, use_container_width=True)
        else:
            st.info(f"No games scheduled for {selected_date.strftime('%A, %B %d, %Y')}")

with tab4:
    st.header("NBA Prospect Distribution by School/Country")
    
    # ==================================================================================== Chart
    
    school_summary = draft_df.groupby(['School'])['Player'].count()
    school_summary = school_summary.reset_index()
    school_summary = school_summary.rename(columns={'School': 'School/Country', 'Player': 'Total'})
    school_summary = school_summary.sort_values(by='Total', ascending=False)
    
    # Create a figure and axis with increased height to prevent overlap
    fig, ax = plt.subplots(figsize=(8, 12))

    # Choose a colormap
    cmap = plt.get_cmap("crest")
    
    values = np.array(school_summary['Total'])
    
    # Normalize values
    norm = plt.Normalize(values.min(), values.max())
    
    # Generate colors (same values get same colors)
    colors = [cmap(norm(value)) for value in values]
    
    # Create a bar plot of Schools with the most prospects
    bars = sns.barplot(
        data=school_summary,
        x="Total",
        y="School/Country",
        hue="School/Country",
        ax=ax,
        palette=colors,
        legend=False
    )
    
    # Add value labels inside the bars in white
    for i, (value, bar) in enumerate(zip(school_summary['Total'], ax.patches)):
        ax.text(
            bar.get_width() - 0.2,  # Position near the end of the bar
            bar.get_y() + bar.get_height() / 2,  # Center vertically
            str(value),  # The value to display
            ha='right',  # Right-align the text
            va='center',  # Center vertically
            color='white',  # White text
            fontsize=10,
            fontweight='bold'
        )
    
    # Set labels and title
    ax.set_xlabel("Number of NBA Prospects")
    ax.set_ylabel("School/Country")
    
    # Set x-axis ticks to only show 0, 1, 2, 3
    ax.set_xticks([0, 1, 2, 3])
    
    # Display the plot in Streamlit
    st.pyplot(fig)

st.divider()
# ==================================================================================== Footer
col1, col2, col3 = st.columns(3)

with col1:
    st.header("Sources")
    url = "https://www.nbadraft.net/nba-mock-drafts/?year-mock=2026"
    ## url = "https://www.nbadraft.net/nba-mock-drafts/?year-mock=2025"
    st.write("[nbadraft.net mock draft board](%s)" % url)
    single_date = get_eastern_today() + timedelta(days=1)  # Start with tomorrow (Eastern time)
    date_str = single_date.strftime("%Y%m%d")
    url = f"https://www.espn.com/mens-college-basketball/schedule/_/date/{date_str}"
    st.write("[espn.com ncaa schedule](%s)" % url)
    url = "https://www.jstew.info"
    st.write("[created by jstew.info](%s)" % url)
    
    # Show current Eastern time for reference
    eastern_time = get_eastern_now()
    st.caption(f"Eastern Time: {eastern_time.strftime('%I:%M %p ET')}")

with col2:
    st.text("")

with col3:
    st.image("static/logo.png", width=200)
