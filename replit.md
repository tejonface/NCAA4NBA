# Overview

This project is a **Flask web application with PostgreSQL backend** for scraping and analyzing NBA draft data and NCAA basketball schedules. The application scrapes live data from external sources (nbadraft.net and ESPN), stores it in a PostgreSQL database, and presents NBA mock draft information with player rankings, teams, physical attributes, and school affiliations through custom HTML/CSS templates. Originally built with Streamlit, the app was fully migrated to Flask to achieve complete design freedom and better performance through database persistence.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Application Framework
- **Backend**: Flask web framework with PostgreSQL database
  - Chosen for complete control over HTML/CSS design (vs Streamlit constraints)
  - Separates data layer (database) from presentation layer (templates)
  - Connection pooling (psycopg2.pool.SimpleConnectionPool) for scalability
  - Context managers ensure no connection leaks
  - All routes use nested `with` blocks for safe resource cleanup
- **Frontend/UI**: Custom HTML templates with Jinja2 and CSS
  - Full design freedom - complete control over layout, styling, interactivity
  - No framework limitations - custom card layouts, hover effects, transitions
  - Layout: Centered card-based design with shadows and modern styling
  - **Tab Organization**: Four tabs organize different views with custom CSS styling
    - Draft Board: Main table with team logos (medium size) and upcoming games
    - Super Matchups: Games with prospects on both teams
    - Games by Date: Simple calendar picker for viewing specific dates
    - Prospect Distribution: Bar chart (8x12 inches for readability)
  - **Tab Styling**: Custom CSS for enhanced UX
    - Larger tabs (60px height, 18px font) for easier clicking and readability
    - Background colors: #f0f2f6 (inactive), #4CAF50 green (active)
    - Hover effects (#e0e3e9) for better interactivity
    - Rounded corners and 8px spacing between tabs
  - **Header Layout**: Clean title with info popover (ℹ️ icon)
    - Popover contains "About" section with app description
    - Popover contains "Data Info" section with date range, refresh interval, and refresh button
    - Minimizes clutter while keeping info accessible
- **Timezone Handling**: Eastern Time (America/New_York)
  - All date calculations use Eastern timezone (standard for US college basketball)
  - Helper functions: `get_eastern_now()` and `get_eastern_today()`
  - Cache metadata stores timestamps with Eastern timezone offset
  - Game times displayed in "Nov 8, 9:00 PM" format
  - Column labeled "Game Time (ET)" but individual times don't show "ET" suffix
  - Footer displays current Eastern time for user reference

## Data Processing Pipeline
- **Database**: PostgreSQL with three tables
  - `prospects`: Stores draft prospect data (rank, team, player info, school)
  - `games`: Stores NCAA game schedule (date, time, teams, TV network)
  - `game_prospects`: Junction table linking prospects to their games
  - Schema defined in `schema.sql` for version control
  - Proper indexes on frequently queried columns (rank, school, game_date)
  - CASCADE constraints for referential integrity
- **Web Scraping**: BeautifulSoup4 with requests library (standalone `scraper.py`)
  - Scrapes HTML tables from nbadraft.net for mock draft data
  - Targets specific table IDs (`nba_mock_consensus_table` and `nba_mock_consensus_table2`)
  - Populates PostgreSQL database instead of returning DataFrames
  - Can be run independently on schedule to keep data fresh
  - **TV Network Extraction**: Smart extraction from ESPN schedule cells
    - `extract_cell_content()` helper function handles both text and image elements
    - Extracts alt text from TV network logo images (e.g., ESPN, FOX, FS1, BTN)
    - Filters out ESPN's base64 lazy-load placeholders (strings starting with "YH5")
    - Falls back to parsing image src URLs when alt text is unavailable
    - Final fallback to text content for cells without images
  - Rationale: Direct data extraction from source ensures real-time accuracy

- **Data Manipulation**: Pandas DataFrames
  - Primary data structure for storing and manipulating scraped data
  - Provides efficient tabular data operations
  - Standard columns: Rank, Team, Player, Height, Weight, Position, School, Conference

## Data Persistence Strategy
- **PostgreSQL Database**: Primary data storage
  - No caching needed - instant page loads from database
  - Scraper runs independently to populate/update data
  - Connection pooling handles concurrent requests efficiently
  - Database queries optimized with proper indexes
  - Data persists across app restarts
- **Scraper Execution**: Manual or scheduled runs
  - Run `python scraper.py` to refresh prospect and game data
  - Can be scheduled with cron for automatic daily updates
  - Separate from web app - no scraping delays during page loads

## Data Visualization
- **Libraries**: Matplotlib and Seaborn
  - Chart size: 8x12 inches (increased height to prevent text/label overlap)
  - Seaborn provides higher-level statistical plotting interface
  - Matplotlib offers low-level customization capabilities
  - Bar chart includes white value labels inside bars for readability
  - Displayed in dedicated "Prospect Distribution" tab

## Code Organization
- **Separation of Concerns**:
  - `schema.sql`: Database schema definition (version controlled)
  - `scraper.py`: Standalone data collection script
    - `scrape_nba_mock_draft()`: Extracts draft data from nbadraft.net
    - `scrape_ncaa_schedule()`: Scrapes 60 days of NCAA schedules from ESPN
    - Populates PostgreSQL tables
  - `flask_app.py`: Web application
    - 5 routes: Draft Board, Super Matchups, Games by Date, Distribution, API endpoint
    - Connection pooling for scalability
    - Context managers for safe resource cleanup
  - `templates/`: Jinja2 HTML templates
    - `base.html`: Common layout with header, nav, footer, info popover
    - Individual page templates for each route
  - `static/`: CSS and JavaScript assets
    - `css/style.css`: Complete custom styling
    - `js/main.js`: Client-side interactivity

## Application Features
- **Draft Board Display**: Shows 2026 NBA Mock Draft rankings with upcoming game schedules
  - **NBA Team Logos**: Displays official NBA team logos from ESPN's CDN instead of text team names
  - Logo mapping handles all 30 NBA teams with variations (e.g., "Golden State" vs "Golden St.")
  - Automatically strips asterisks from projected picks (e.g., "*Utah" → Utah logo)
  - ImageColumn configuration shows logos at "small" size for compact table layout
- **Super Matchups**: Highlights games featuring top draft prospects on both teams
  - **Player Formatting**: Players grouped by school with clean multi-line display
  - Format shows school name as header with bullet-pointed players beneath:
    ```
    Florida:
      • #15 Boogie Fland
      • #28 Thomas Haugh
    
    Arizona:
      • #23 Brayden Burries
    ```
  - Table height increased to 600px to accommodate multi-line rows
  - Players column uses TextColumn configuration with "large" width for readability
- **Date Selection**: Simple interactive calendar with clean UX
  - **Game Counts**: Displays number of unique matchups for selected date (e.g., "5 games on Monday, November 4, 2025")
  - **Empty State Handling**: Shows clear message when no games scheduled
  - **Deduplication**: Accurately counts unique matchups (prevents double-counting when prospects on both teams)
  - **Session State**: Selected date persists across page interactions and refreshes
- **Prospect Tracking**: Automatically matches NCAA players with their draft rankings
- **Data Visualization**: Bar chart showing prospect distribution by school/country with white value labels
- **Real-Time Data**: 1-hour cache refresh for up-to-date information
- **Manual Refresh**: User-triggered data refresh button to clear cache and reload latest schedules
- **Extended Coverage**: 60-day schedule coverage allows users to plan ahead for the rest of the season

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
  - Scrapes upcoming 60 days starting from yesterday (to account for timezone differences)
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