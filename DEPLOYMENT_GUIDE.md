# Deploying to Streamlit Cloud (ncaa4nba.streamlit.app)

This guide shows you how to deploy `app2.py` to your existing Streamlit Cloud app to replace your current codebase.

## What's Different in app2.py

- **Self-contained**: All scraping and display logic in one file
- **No Replit dependencies**: Uses only standard Python packages
- **In-memory caching**: Data cached for 2 hours using `@st.cache_data`
- **Works on Streamlit Cloud**: No external storage needed

## Files to Copy to GitHub

From this Replit project, copy these files to your GitHub repo:

1. **`app2.py`** → Rename to `app.py` in your GitHub repo
2. **`requirements_streamlit.txt`** → Rename to `requirements.txt` in your GitHub repo
3. **`.streamlit/config.toml`** (if you want custom config)

## Step-by-Step Deployment

### 1. Prepare Your GitHub Repository

```bash
# In your local GitHub repo folder:
# 1. Copy app2.py and rename it
cp /path/to/replit/app2.py ./app.py

# 2. Copy requirements
cp /path/to/replit/requirements_streamlit.txt ./requirements.txt

# 3. Commit and push
git add app.py requirements.txt
git commit -m "Update to combined scraper + display app"
git push origin main
```

### 2. Streamlit Cloud Will Auto-Deploy

Since your GitHub repo is already connected to `ncaa4nba.streamlit.app`, Streamlit Cloud will:
- Detect the changes automatically
- Rebuild the app with new dependencies
- Deploy the new version

**⏱ Deployment time**: Usually 2-5 minutes

### 3. Monitor the Deployment

1. Go to https://share.streamlit.io/
2. Find your `ncaa4nba` app
3. Click on it to see deployment logs
4. Wait for "Your app is live!" message

## First Load Behavior

**Important**: The first time someone visits the app, it will:
1. Show "Loading NBA Draft and NCAA Schedule data..." for ~10-30 seconds
2. Scrape data from nbadraft.net and ESPN
3. Display the full app

**Subsequent loads**: Data is cached for 2 hours, so loads are instant!

## Features

✅ **Auto-refresh**: Data auto-refreshes every 2 hours  
✅ **Manual refresh**: Click the 🔄 button to reload data anytime  
✅ **Live game detection**: Shows 🔴 Live for games in progress  
✅ **All 4 tabs**: Draft Board, Super Matchups, Games by Date, Prospect Distribution  
✅ **60 days of schedule**: Automatically scrapes next 60 days

## Troubleshooting

### App shows error on Streamlit Cloud

**Check deployment logs** for specific errors. Common issues:
- **Missing dependencies**: Make sure `requirements.txt` has all packages
- **Scraping blocked**: Some sites block cloud IPs occasionally - just refresh

### App loads slowly

**Normal**: First load takes 10-30 seconds to scrape data. This is expected.  
**After 2 hours**: Cache expires, so next visitor triggers a new scrape.

### Want faster refresh?

Change the TTL in app2.py (line 65 and others):
```python
@st.cache_data(ttl=7200)  # 7200 seconds = 2 hours
# Change to 3600 for 1 hour, 10800 for 3 hours, etc.
```

## Comparison: Before vs After

| Feature | Old (PyCharm) | New (app2.py) |
|---------|---------------|---------------|
| Files | Multiple files | Single file |
| Storage | External DB? | In-memory cache |
| Scraping | Separate process? | Built-in |
| Dependencies | Many | Minimal (8 packages) |
| Deploy | Complex | Git push = done |
| Maintenance | Update multiple parts | Update one file |

## Keeping Your URL

Since you're updating an existing Streamlit Cloud app, your URL stays the same:
**https://ncaa4nba.streamlit.app** ✨

## Questions?

- **Data freshness**: Scraped every 2 hours automatically
- **Cost**: Free on Streamlit Cloud Community
- **Performance**: Fast after first load (cached)
- **Reliability**: Streamlit handles all infrastructure

---

**You're all set!** Just copy the files, push to GitHub, and watch Streamlit Cloud deploy automatically.
