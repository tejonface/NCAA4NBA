# Overview

This project is a **Streamlit web application** for scraping and analyzing NBA draft data and NCAA basketball schedules. The application fetches live data from external sources (nbadraft.net) and presents NBA mock draft information with player rankings, teams, physical attributes, and school affiliations. The application is designed to provide basketball analytics and scouting information with data visualization capabilities using matplotlib and seaborn.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Application Framework
- **Frontend/UI**: Streamlit framework for building interactive web applications with Python
  - Chosen for rapid prototyping and built-in interactive components
  - Simplifies deployment and user interface creation without HTML/CSS/JS
  - Trade-off: Less flexibility than traditional web frameworks but much faster development
  - Layout: Centered layout (max-width ~980px) to prevent excessive stretching on large external monitors
  - Tables use container width for optimal display within centered layout
- **Timezone Handling**: Pacific Time (America/Los_Angeles)
  - All date calculations use Pacific timezone (not server UTC time)
  - Helper functions: `get_pacific_now()` and `get_pacific_today()`
  - Cache metadata stores timestamps with Pacific timezone offset
  - Ensures game schedules align with West Coast sports viewing times
  - Footer displays current Pacific time for user reference

## Data Processing Pipeline
- **Web Scraping**: BeautifulSoup4 with requests library
  - Scrapes HTML tables from nbadraft.net for mock draft data
  - Targets specific table IDs (`nba_mock_consensus_table` and `nba_mock_consensus_table2`)
  - Combines data from multiple tables into single DataFrame
  - Rationale: Direct data extraction from source ensures real-time accuracy

- **Data Manipulation**: Pandas DataFrames
  - Primary data structure for storing and manipulating scraped data
  - Provides efficient tabular data operations
  - Standard columns: Rank, Team, Player, Height, Weight, Position, School, Conference

## Caching Strategy
- **Two-Layer Caching System**:
  1. **File-based Cache**: Persistent JSON storage in `schedule_cache/` directory
     - `ncaa_schedule.json`: Stores all scraped game data
     - `metadata.json`: Tracks last update timestamps for each date
     - Smart refresh: Recent games (within 7 days) refresh every 30 minutes; future games refresh every 6 hours
     - Survives app restarts and provides significant performance boost
  2. **Streamlit Cache**: `@st.cache_data` decorator with 1800-second TTL (30 minutes)
     - Second layer on top of file cache for in-memory speed
     - Manual refresh button clears both caches for immediate updates
- **Parallel Scraping**: ThreadPoolExecutor with 10 workers
  - Only scrapes missing or stale dates based on file cache metadata
  - First load: ~15 seconds (all 60 dates in parallel)
  - Subsequent loads: ~2-3 seconds (only 2-3 dates need refresh)
  - 95% performance improvement on typical reloads

## Data Visualization
- **Libraries**: Matplotlib and Seaborn
  - Chart size: 8x6 inches for optimal viewing on laptop and external monitors
  - Seaborn provides higher-level statistical plotting interface
  - Matplotlib offers low-level customization capabilities
  - Bar chart includes white value labels inside bars for readability

## Code Organization
- **Modular Functions**: Separate functions for each scraping task
  - `scrape_nba_mock_draft()`: Handles NBA draft data extraction from nbadraft.net
  - `scrape_ncaa_schedule()`: Scrapes 60 days of NCAA basketball schedules from ESPN (covers ~2 months)
  - `get_players_from_school()`: Matches draft prospects with their upcoming games
  - Promotes code reusability and maintainability

## Application Features
- **Draft Board Display**: Shows 2026 NBA Mock Draft rankings with upcoming game schedules
  - **NBA Team Logos**: Displays official NBA team logos from ESPN's CDN instead of text team names
  - Logo mapping handles all 30 NBA teams with variations (e.g., "Golden State" vs "Golden St.")
  - Automatically strips asterisks from projected picks (e.g., "*Utah" → Utah logo)
  - ImageColumn configuration shows logos at optimal "small" size for table readability
- **Super Matchups**: Highlights games featuring top draft prospects on both teams
- **Date-Based Filtering**: Interactive calendar date picker for viewing games on any specific day within the 60-day range
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