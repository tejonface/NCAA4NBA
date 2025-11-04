# Overview

This project is a **Streamlit web application** for analyzing NBA draft data and NCAA basketball schedules. The application consists of two main components:

1. **scraper.py**: A standalone web scraper that fetches data from external sources (nbadraft.net and ESPN) and saves it to CSV files
2. **app.py**: A Streamlit web application that loads pre-scraped data and presents NBA mock draft information with player rankings, teams, physical attributes, and school affiliations

This separation ensures the Streamlit app loads instantly without waiting for web scraping on every page load. The application provides basketball analytics and scouting information with data visualization capabilities using matplotlib and seaborn.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Application Framework
- **Frontend/UI**: Streamlit framework for building interactive web applications with Python
  - Chosen for rapid prototyping and built-in interactive components
  - Simplifies deployment and user interface creation without HTML/CSS/JS
  - Trade-off: Less flexibility than traditional web frameworks but much faster development
  - Layout: Centered layout (max-width ~980px) to prevent excessive stretching on large external monitors
  - **Tab Organization**: Four tabs organize different views with custom CSS styling
    - Draft Board: Main table with team logos (medium size) and upcoming games
    - Super Matchups: Games with prospects on both teams
    - Games by Date: Compact date picker layout with game count on same line
    - Prospect Distribution: Bar chart (8x12 inches for readability)
  - **Professional Formatting** (November 2025):
    - Consistent title case for all headers ("Super Matchups", not "SUPER MATCHUPS")
    - Visual hierarchy using st.caption() for descriptions (lighter, smaller text)
    - Title case column names across all tables (Away, Home, TV, Players)
    - Proper capitalization in footer links and labels
    - Two-column layout for date picker: input on left, game count on right
  - **Tab Styling**: Custom CSS for enhanced UX
    - Larger tabs (60px height, 16px font) for easier clicking and readability
    - Modern blue theme: #f8fafc (inactive), #3b82f6 primary blue (active)
    - Smooth hover effects with subtle lift animation (translateY(-2px))
    - Rounded corners, borders, and box shadows for depth
    - 8px spacing between tabs
  - **Header Layout**: Clean title with info popover (ℹ️ icon)
    - Popover contains "About" section with app description
    - Popover contains "Data Info" section with date range, refresh interval, and refresh button
    - Minimizes clutter while keeping info accessible
  - **Design System**: Modern, cohesive blue/gray color palette (November 2025)
    - **Primary Colors**: #3b82f6 (blue), #2563eb (dark blue), #60a5fa (light blue)
    - **Neutral Colors**: #f8fafc (bg-light), #ffffff (bg-card), #e2e8f0 (borders)
    - **Text Colors**: #1e293b (primary), #64748b (secondary)
    - **Table Enhancements**:
      - Blue header backgrounds (#3b82f6) with white text, sticky positioning
      - Alternating row colors (#f8fafc for even rows) for better scanability
      - Hover effects (#e0f2fe background) with smooth transitions
      - Subtle shadows and borders for depth
    - **Interactive Elements**:
      - Loading spinner with blue color matching theme
      - Smooth transitions (0.2s ease) on all interactive elements
      - Enhanced button hover states with lift effect (translateY(-1px))
      - Focus states on date inputs with blue border and shadow
      - Polished popover styling with shadows and borders
    - **Chart Styling**:
      - Modern blue gradient palette (5 shades: #93c5fd to #1d4ed8)
      - Clean background (#f8fafc), subtle borders on bars
      - Improved typography and spacing
      - Subtle grid lines for easier reading
      - Minimalist spine styling (top/right removed)
- **Timezone Handling**: Eastern Time (America/New_York)
  - All date calculations use Eastern timezone (standard for US college basketball)
  - Helper functions: `get_eastern_now()` and `get_eastern_today()`
  - Cache metadata stores timestamps with Eastern timezone offset
  - Game times displayed in "Nov 8, 9:00 PM" format
  - Column labeled "Game Time (ET)" but individual times don't show "ET" suffix
  - Footer displays current Eastern time for user reference

## Data Processing Pipeline

### Web Scraping (scraper.py)
- **Standalone Scraper**: Runs independently from the Streamlit app
  - Execute with: `python scraper.py`
  - Saves data to `data/` directory with three files:
    - `draft_data.csv`: NBA draft prospects (60 players)
    - `schedule_data.csv`: NCAA basketball schedule (30 days, ~1500 games)
    - `scrape_metadata.json`: Last scrape time and data counts
  - **Web Scraping with BeautifulSoup4**:
    - Scrapes HTML tables from nbadraft.net for mock draft data
    - Targets specific table IDs (`nba_mock_consensus_table` and `nba_mock_consensus_table2`)
    - Combines data from multiple tables into single DataFrame
    - **TV Network Extraction**: Smart extraction from ESPN schedule cells
      - `extract_cell_content()` helper function handles both text and image elements
      - Extracts alt text from TV network logo images (e.g., ESPN, FOX, FS1, BTN)
      - Filters out ESPN's base64 lazy-load placeholders (strings starting with "YH5")
      - Falls back to parsing image src URLs when alt text is unavailable
      - Final fallback to text content for cells without images
  - **Parallel Scraping**: ThreadPoolExecutor with 10 workers for 30 concurrent date requests
  - **Column Normalization**: Renames columns before saving to ensure consistent CSV format
    - MATCHUP → AWAY, '' → HOME, tickets → TICKETS, location → LOCATION, logo espnbet → ODDS_BY

### Data Loading (app.py)
- **File-Based Loading**: Loads pre-scraped data from CSV files in `data/` directory
  - Fast page loads (no web scraping on user visits)
  - `@st.cache_data` decorator caches loaded DataFrames in memory
  - **Automatic Cache Invalidation**: Uses file modification timestamps to detect when scraper updates data
    - Each load function checks the CSV file's modification time
    - When scraper runs and updates files, cache automatically invalidates
    - Next visitor gets fresh data without manual intervention
  - Graceful error handling if data files are missing (prompts user to run scraper)
  - Manual refresh button available for immediate cache clearing

- **Data Manipulation**: Pandas DataFrames
  - Primary data structure for storing and manipulating scraped data
  - Provides efficient tabular data operations
  - Standard columns: Rank, Team, Player, Height, Weight, Position, School, Conference

## Data Storage Strategy
- **File-Based Storage**: All scraped data saved to CSV files in `data/` directory
  - **draft_data.csv**: 60 NBA draft prospects with ranks, schools, physical stats
  - **schedule_data.csv**: 30 days of NCAA basketball games (~1500 games)
  - **scrape_metadata.json**: Tracks last scrape time and data counts for user reference
  - Persistent storage survives app restarts
  - Decouples web scraping from app loading for instant page loads
  
- **Streamlit Caching with Auto-Refresh**: `@st.cache_data` decorator for in-memory performance
  - Caches loaded DataFrames to avoid repeated disk reads
  - **File Modification Time Tracking**: Automatically detects when CSV files are updated
    - `get_file_mtime()` helper retrieves file modification timestamps
    - Timestamps are part of the cache key, so file updates invalidate cached data
    - Zero overhead - single `os.path.getmtime()` call per request
  - Manual refresh button available for immediate updates
  - User can see last scrape time in the info popover
  
- **Update Workflow**: 
  1. **Scheduled Scraper** (Recommended): Set up Replit Scheduled Deployment to run `python scraper.py` daily at 6 AM
     - Scraper updates CSV files automatically
     - Next visitor after 6 AM gets fresh data (cache auto-invalidates based on file modification time)
     - No manual intervention required
  2. **Manual Scraper**: Run `python scraper.py` anytime to fetch fresh data (takes ~10-15 seconds)
     - Updates CSV files immediately
     - App detects changes and reloads data on next page visit
  3. **Force Refresh**: Users can click "Refresh Data" button to clear cache and reload immediately

## Data Visualization
- **Libraries**: Matplotlib and Seaborn
  - Chart size: 8x12 inches (increased height to prevent text/label overlap)
  - Seaborn provides higher-level statistical plotting interface
  - Matplotlib offers low-level customization capabilities
  - Bar chart includes white value labels inside bars for readability
  - Displayed in dedicated "Prospect Distribution" tab

## Code Organization
- **Separation of Concerns**: Web scraping and UI are completely decoupled
  - **scraper.py**: All web scraping logic (BeautifulSoup4, requests, parallel processing)
    - `scrape_nba_mock_draft()`: Handles NBA draft data extraction from nbadraft.net
    - `scrape_ncaa_schedule()`: Scrapes 30 days of NCAA basketball schedules from ESPN
    - `extract_cell_content()`: Helper for extracting TV network info from HTML
    - `run_scraper()`: Main orchestrator that runs all scrapers and saves files
  - **app.py**: Streamlit UI and data presentation
    - `load_draft_data()`: Loads draft prospects from CSV with caching
    - `load_schedule_data()`: Loads game schedule from CSV with caching
    - `get_players_from_school()`: Matches draft prospects with their upcoming games
    - Data transformation, table building, and visualization
  - Promotes code reusability, maintainability, and faster page loads

## Application Features
- **Draft Board Display**: Shows 2026 NBA Mock Draft rankings with upcoming game schedules
  - **NBA Team Logos**: Displays official NBA team logos from ESPN's CDN instead of text team names
  - Logo mapping handles all 30 NBA teams with variations (e.g., "Golden State" vs "Golden St.")
  - Automatically strips asterisks from projected picks (e.g., "*Utah" → Utah logo)
  - ImageColumn configuration shows logos at "small" size for compact table display
- **Super Matchups**: Highlights games featuring top draft prospects on both teams
- **Date Selection**: Simple interactive calendar with clean UX
  - **Game Counts**: Displays number of unique matchups for selected date (e.g., "5 games on Monday, November 4, 2025")
  - **Empty State Handling**: Shows clear message when no games scheduled
  - **Deduplication**: Accurately counts unique matchups (prevents double-counting when prospects on both teams)
  - **Session State**: Selected date persists across page interactions and refreshes
- **Prospect Tracking**: Automatically matches NCAA players with their draft rankings
- **Data Visualization**: Bar chart showing prospect distribution by school/country with white value labels
- **Smart Caching**: Tiered refresh intervals (30min for soon, 12hr for near-term, 24hr for far-future)
- **Manual Refresh**: User-triggered data refresh button to clear cache and reload latest schedules
- **Extended Coverage**: 30-day schedule coverage for faster loading (covers next month of games)

# External Dependencies

## Third-Party Libraries
- **streamlit**: Web application framework and UI rendering
- **pandas**: Data manipulation and analysis
- **requests**: HTTP client for web scraping
- **beautifulsoup4**: HTML/XML parsing for web scraping
- **numpy**: Numerical computing support
- **seaborn**: Statistical data visualization
- **matplotlib**: Plotting and charting library
- **tabulate**: Table formatting (imported but not yet utilized)

## External Data Sources
- **nbadraft.net**: Primary data source for NBA mock draft information
  - URL pattern: `https://www.nbadraft.net/nba-mock-drafts/?year-mock=2026`
  - Provides consensus mock draft rankings
  - Data includes player rankings, team assignments, physical stats, schools
  - Note: Relies on consistent HTML structure; changes to website may break scraping

- **ESPN**: NCAA basketball schedule data
  - URL pattern: `https://www.espn.com/mens-college-basketball/schedule/_/date/{YYYYMMDD}`
  - Provides daily NCAA basketball game schedules
  - Scrapes upcoming 30 days starting from today (covers next month, Eastern timezone)
  - Data includes team matchups, game times, TV coverage, and venue information
  - Note: Requires User-Agent header for successful requests

## Python Standard Library
- **datetime**: Date and time manipulation for scheduling features
  - Imports: `date`, `timedelta`, `datetime`
  - Used for time-based data filtering and scheduling operations

## Deployment Considerations
- Application designed to run as Streamlit server
- No database required (data fetched on-demand from external sources)
- Stateless architecture with caching layer for performance