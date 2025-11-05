# Overview

This is a Streamlit web application that provides NBA draft prospect tracking and scheduling information. The application scrapes data from two primary sources: NBA Draft Net for mock draft consensus data and ESPN for NCAA men's college basketball schedules. The purpose is to help users track top NBA draft prospects and monitor their upcoming college basketball games.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture

**Technology**: Streamlit framework for Python-based web applications

**Rationale**: Streamlit provides a simple, declarative approach to building data-driven web applications without requiring separate frontend development. This allows rapid prototyping and deployment of data visualization and analysis tools with minimal code.

**Design Pattern**: Single-page application with reactive components that automatically update when data changes.

## Backend Architecture

**Technology**: Python with synchronous request handling

**Architecture Pattern**: Monolithic application structure with function-based data processing

**Key Components**:
- Web scraping functions using BeautifulSoup4 for HTML parsing
- Data transformation using Pandas DataFrames
- Caching mechanism via Streamlit's `@st.cache_data` decorator with 30-minute TTL (1800 seconds)

**Rationale**: The synchronous approach is sufficient for this use case since the application serves individual users and doesn't require handling concurrent requests. The caching strategy reduces unnecessary web scraping requests and improves response times.

## Data Storage

**Approach**: In-memory data storage with no persistent database

**Rationale**: The application deals with frequently changing external data (draft rankings, game schedules). Caching scraped data in memory for 30 minutes balances freshness with performance. No user-generated data requires persistence.

**Data Flow**:
1. Data is scraped from external sources on-demand
2. Cached in memory for 30 minutes
3. Transformed into Pandas DataFrames for analysis
4. Presented directly to users through Streamlit components

## Authentication & Authorization

**Current State**: No authentication mechanism implemented

**Rationale**: The application provides read-only access to publicly available data, eliminating the need for user authentication or authorization controls.

# External Dependencies

## Third-Party Services & APIs

### NBA Draft Net
- **URL Pattern**: `https://www.nbadraft.net/nba-mock-drafts/?year-mock={year}`
- **Purpose**: Source for NBA mock draft consensus data
- **Data Extracted**: Player rankings, team assignments, physical measurements (height, weight, position), school affiliation, and class year
- **Tables Scraped**: Two tables identified by IDs `nba_mock_consensus_table` and `nba_mock_consensus_table2`
- **Method**: HTTP GET requests with BeautifulSoup HTML parsing

### ESPN College Basketball Schedule
- **URL Pattern**: `https://www.espn.com/mens-college-basketball/schedule/_/date/{YYYYMMDD}`
- **Purpose**: Source for NCAA men's college basketball game schedules
- **Data Extracted**: Game matchups and scheduling information
- **Method**: HTTP GET requests with custom User-Agent headers to avoid blocking
- **Schedule Range**: Configured to scrape 7 days of upcoming games

## Python Libraries

### Core Dependencies
- **streamlit**: Web application framework
- **pandas**: Data manipulation and analysis
- **requests**: HTTP library for web scraping
- **beautifulsoup4**: HTML parsing library
- **numpy**: Numerical computing support
- **seaborn**: Statistical data visualization
- **matplotlib**: Plotting library
- **tabulate**: Table formatting utility

### Development Environment
- **Python Version**: 3.11 (specified in devcontainer configuration)
- **Container**: Microsoft Dev Container for Python development
- **IDE Support**: VS Code with Python and Pylance extensions

## Deployment Configuration

**Platform**: GitHub Codespaces / VS Code Dev Containers

**Port Configuration**: Application runs on port 8501 with auto-forwarding enabled

**Streamlit Server Settings**: 
- CORS disabled for development
- XSRF protection disabled for development