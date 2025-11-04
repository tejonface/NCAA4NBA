# Automated Scraper Schedule Setup

## Overview
The scraper has been configured to fetch the complete NCAA basketball season (continuing until 10 consecutive days with no games). To keep your data fresh, you should set up automatic daily scraping.

## Last Scrape Results
- **Date**: November 4, 2025 at 5:34 PM ET
- **Games fetched**: 5,715 games across 122 dates
- **Coverage**: Through early March 2026 (end of regular season)

## Setting Up Scheduled Deployments

To automatically run the scraper daily:

1. **Access Deployments**
   - Open the Deployments workspace tool in Replit

2. **Create Scheduled Deployment**
   - Select "Scheduled" deployment type
   - Click "Set up your published app"

3. **Configure Schedule**
   - **Run Command**: `python scraper.py`
   - **Schedule**: "Every day at 6 AM" (or your preferred time)
   - The AI will convert this to a cron expression automatically

4. **Deploy**
   - Save and deploy the scheduled task
   - Replit will run it automatically at your specified time

## Manual Scraper Execution

You can also run the scraper manually anytime:

```bash
python scraper.py
```

This will:
- Fetch updated NBA draft rankings
- Scrape NCAA schedule through end of season
- Create backups of existing data before overwriting
- Validate data before saving (ensures no corrupt data)

## Data Refresh in the App

The Streamlit app automatically detects when new data is available:
- **Cache Invalidation**: Checks file modification times
- **Smart Refresh Intervals**:
  - Today's games: 30 minutes
  - Next 7 days: 12 hours  
  - Future games: 48 hours
- **Force Refresh**: Use the button in the info popover (ℹ️) to immediately reload

## Monitoring

After the scheduled scraper runs, check:
- `data/scrape_metadata.json` - shows last scrape time and counts
- The app's info popover displays the last update time
- Backup files (`.backup`) are created before each scrape
