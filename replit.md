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
- **Streamlit Cache**: `@st.cache_data` decorator with 3600-second TTL (1 hour)
  - Reduces redundant HTTP requests to external sources
  - Improves application performance and reduces load on scraped websites
  - 1-hour refresh ensures reasonably fresh data while minimizing requests
  - Rationale: Balances data freshness with performance optimization, especially with extended 60-day scraping range

## Data Visualization
- **Libraries**: Matplotlib and Seaborn
  - Prepared for creating statistical visualizations and charts
  - Seaborn provides higher-level statistical plotting interface
  - Matplotlib offers low-level customization capabilities

## Code Organization
- **Modular Functions**: Separate functions for each scraping task
  - `scrape_nba_mock_draft()`: Handles NBA draft data extraction from nbadraft.net
  - `scrape_ncaa_schedule()`: Scrapes 60 days of NCAA basketball schedules from ESPN (covers ~2 months)
  - `get_players_from_school()`: Matches draft prospects with their upcoming games
  - Promotes code reusability and maintainability

## Application Features
- **Draft Board Display**: Shows 2026 NBA Mock Draft rankings with upcoming game schedules
- **Super Matchups**: Highlights games featuring top draft prospects on both teams
- **Date-Based Filtering**: Interactive segmented date selector for viewing games on any specific day within the 60-day range
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