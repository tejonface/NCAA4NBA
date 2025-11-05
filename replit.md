# Overview

This project is a **Streamlit web application** designed for analyzing NBA draft data and NCAA basketball schedules. It comprises a standalone web scraper (`scraper.py`) that fetches data from `nbadraft.net` and `ESPN`, and a Streamlit application (`app.py`) that loads this pre-scraped data to present NBA mock draft information, player rankings, team affiliations, physical attributes, and school data. The application offers basketball analytics and scouting insights, incorporating data visualization for an enhanced user experience. The core purpose is to provide up-to-date scouting information efficiently, without requiring real-time web scraping during user interaction.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Application Framework
- **Frontend/UI**: Streamlit, chosen for rapid prototyping, interactive components, and simplified UI development in Python.
  - **Layout**: Wide mode with a custom-centered container (max-width 1400px) for optimal table display.
  - **Tab Organization**: Four distinct tabs: "Draft Board" (main table with team logos and upcoming games), "Super Matchups" (games with multiple top prospects), "Games by Date" (date-filtered schedule using `@st.fragment` for partial reruns), and "Prospect Distribution" (bar chart of prospect origins). Each tab includes descriptive captions and uses `use_container_width=True` for responsiveness.
  - **Professional Formatting**: Consistent title case for headers and column names, visual hierarchy using `st.caption()`, and clear footer links.
  - **Tab Styling**: Custom CSS for larger tabs (60px height, 16px font), a modern blue theme (#f8fafc inactive, #3b82f6 active), hover effects, rounded corners, and box shadows.
  - **Header Layout**: Clean title with an info popover (ℹ️ icon) for "About", "Data Info", "Smart Refresh" sections, and "Created by" attribution with clickable logo linking to jstew.info.
  - **Design System**: Cohesive blue/gray color palette (`#3b82f6`, `#2563eb`, `#60a5fa` for primary; `#f8fafc`, `#ffffff`, `#e2e8f0` for neutral) for consistent UI elements, including table enhancements (blue headers, alternating row colors, hover effects) and interactive elements (loading spinners, button hover states, focus states).
  - **Chart Styling**: Modern blue gradient palette for charts, clean background, subtle grid lines, and improved typography.
- **Timezone Handling**: All date and time calculations use Eastern Time (America/New_York), with helper functions `get_eastern_now()` and `get_eastern_today()`. Game times are displayed in a concise format (e.g., "Nov 8, 9:00 PM").

## Data Processing Pipeline
- **Web Scraping (`scraper.py`)**: A standalone script that fetches data from `nbadraft.net` (mock draft) and `ESPN` (NCAA schedule).
  - **Output**: Saves `draft_data.csv`, `schedule_data.csv`, and `scrape_metadata.json` to the `data/` directory.
  - **Reliability**: Features atomic writes, automatic backups, validation checks (minimum data thresholds), and robust error handling to preserve existing data if scraping fails.
  - **Technology**: Uses `BeautifulSoup4` for HTML parsing. Includes smart TV network extraction from ESPN cells, handling both text and image elements.
  - **Efficiency**: Employs `ThreadPoolExecutor` with 10 workers for parallel scraping in 30-day batches. Scraping continues until 10 consecutive days with no games are found, ensuring complete season coverage.
  - **Normalization**: Renames columns for consistency before saving.
- **Data Loading (`app.py`)**: Loads pre-scraped data from CSV files.
  - **Caching**: Uses `@st.cache_data` for in-memory caching of DataFrames.
  - **Cache Invalidation**: Automatically invalidates caches based on file modification timestamps (`get_file_mtime()`), ensuring fresh data after scraper runs.
  - **Error Handling**: Gracefully handles missing data files, prompting users to run the scraper.
  - **Data Structure**: Pandas DataFrames are used for efficient data manipulation.

## Data Storage Strategy
- **File-Based Storage**: All scraped data is stored in CSV files within the `data/` directory (`draft_data.csv`, `schedule_data.csv`, `scrape_metadata.json`). This ensures persistent storage and decouples web scraping from app loading.
- **Streamlit Caching**: `@st.cache_data` combined with file modification time tracking ensures fast data access and automatic data refresh when underlying files change. A manual refresh button is also available.
- **Background Scheduler**: Uses APScheduler (`background_scheduler.py`) to automatically refresh data with tiered intervals:
  - Today's games: Every 30 minutes (catches live game status changes)
  - Next 7 days: Every 6 hours (for schedule updates)
  - Draft board: Daily at 6:00 AM ET (for ranking changes)
  - Far-future games: Daily at 6:30 AM ET (for long-term schedule)
- **Thread Safety**: All file updates use threading.Lock to prevent race conditions when concurrent background jobs update the same data files.
- **Partial Updates**: Background jobs use `scrape_date_range()` to update only specific date ranges, avoiding full season re-scrapes and minimizing load time.

## Data Visualization
- **Libraries**: Matplotlib and Seaborn are used for generating charts, specifically a bar chart for prospect distribution by school/country, displayed in the "Prospect Distribution" tab. Charts are sized 6x10 inches for a compact, narrower display with white value labels inside bars.

## Code Organization
- **Separation of Concerns**: `scraper.py` handles all web scraping logic, while `app.py` manages the Streamlit UI, data presentation, and caching. This modularity enhances reusability and maintainability.

## Application Features
- **Draft Board Display**: Shows NBA Mock Draft rankings, team logos (from ESPN's CDN), and upcoming NCAA game schedules.
- **Super Matchups**: Identifies and highlights games featuring top draft prospects from opposing teams.
- **Date Selection**: Provides an interactive calendar with game counts for selected dates and handles empty states.
- **Prospect Tracking**: Matches NCAA players with their NBA draft rankings.
- **Live Game Detection**: Automatically detects and displays live games with "🔴 Live" status for today's games that are currently in progress (within game window: 15 min before start to 3 hours after). Shows "Final" for completed games and formatted times for upcoming/future games.
- **Smart Caching**: Tiered refresh intervals (30 min for today's games, 12 hr for next 7 days, 48 hr for future games) optimizes performance while ensuring fresh data.
- **Manual Refresh**: User-triggered button to clear cache and reload data.
- **Extended Coverage**: NCAA schedule coverage through end of season (scraper continues until 10 consecutive days with no games).
- **Zero Load Delays**: Background scheduler keeps data fresh automatically, so the app loads instantly from cached data without waiting for scraping operations.

# External Dependencies

## Third-Party Libraries
- **streamlit**: Web application framework.
- **pandas**: Data manipulation and analysis.
- **requests**: HTTP client for web scraping.
- **beautifulsoup4**: HTML/XML parsing for web scraping.
- **numpy**: Numerical computing.
- **seaborn**: Statistical data visualization.
- **matplotlib**: Plotting and charting.
- **APScheduler**: Background job scheduler for automatic data refreshes with tiered intervals.

## External Data Sources
- **nbadraft.net**: Primary source for NBA mock draft data (player rankings, teams, stats, schools).
- **ESPN**: Source for NCAA basketball schedule data (game schedules, times, TV coverage, venue info). Requires User-Agent header.

## Python Standard Library
- **datetime**: Date and time manipulation for scheduling features.