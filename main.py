import streamlit as st
import bs4
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import date, timedelta
from seaborn import color_palette
from tabulate import tabulate
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

# Function to scrape NBA draft data
def scrape_nba_mock_draft(url):
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    all_data = []
    for table_id in ["nba_mock_consensus_table", "nba_mock_consensus_table2"]:
        table = soup.find("table", {"id": table_id})
        if table:
            rows = table.find("tbody").find_all("tr")
            for row in rows:
                cols = row.find_all("td")
                cols = [col.text.strip() for col in cols]
                all_data.append(cols)

    df = pd.DataFrame(all_data)
    df.columns = ["Rank", "Team", "Player", "H", "W", "P", "School", "C"]
    return df

# Scrape draft data
draft_url = "https://www.nbadraft.net/nba-mock-drafts/?year-mock=2025"
draft_df = scrape_nba_mock_draft(draft_url)

# Clean Draft Board Schools
draft_df['School_Merge'] = draft_df['School'].str.replace(r'St\.$', 'State', regex=True)
draft_df['School_Merge'] = draft_df['School_Merge'].str.replace(r'^St\.', 'Saint', regex=True)
draft_df['School_Merge'] = draft_df['School_Merge'].str.replace("'", "").str.strip()

# Function to scrape NCAA schedule
def scrape_ncaa_schedule():
    combined_df = pd.DataFrame()
    for i in range(7):
        single_date = date.today() + timedelta(days=i)
        date_str = single_date.strftime("%Y%m%d")
        url = f"https://www.espn.com/mens-college-basketball/schedule/_/date/{date_str}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, "html.parser")
        table = soup.find("table")
        if not table:
            continue
        rows = table.find_all("tr")
        data = [[col.text.strip() for col in row.find_all(["th", "td"])] for row in rows if row.find_all(["th", "td"])]
        df = pd.DataFrame(data)
        if not df.empty:
            df.columns = df.iloc[0]
            df = df.drop(0).reset_index(drop=True)
            df.columns = [df.columns[0]] + [''] + list(df.columns[1:-1])
            df["DATE"] = single_date
            combined_df = pd.concat([combined_df, df], ignore_index=True)
    return combined_df

# Scrape NCAA schedule
combined_df = scrape_ncaa_schedule()

# Rename columns
combined_df = combined_df.rename(columns={
    combined_df.columns[0]: "AWAY",
    combined_df.columns[1]: "HOME",
    combined_df.columns[2]: "TIME (ET)",
    combined_df.columns[3]: "TV",
    combined_df.columns[4]: "TICKETS",
    combined_df.columns[5]: "LOCATION",
    combined_df.columns[6]: "ODDS BY",
    combined_df.columns[7]: "DATE"
})

# Clean team names
combined_df["TEAM"] = combined_df["HOME"].str.replace(r'[@0-9]', '', regex=True).str.strip()
combined_df["TEAM"] = combined_df["TEAM"].str.replace("'", "")
combined_df["TEAM"] = combined_df["TEAM"].str.replace(r'St\.$', 'State', regex=True)
combined_df["TEAM"] = combined_df["TEAM"].str.replace(r'^St\.', 'Saint', regex=True)
combined_df["TEAM_Merge"] = combined_df["TEAM"]
combined_df["TEAM_Merge"] = combined_df["TEAM_Merge"].str.replace("'", "").str.strip()

# Merge draft board with upcoming games
upcoming_games_df = combined_df[combined_df['TEAM_Merge'].isin(draft_df['School_Merge'])]
draft_with_games = pd.merge(draft_df, upcoming_games_df, left_on='School_Merge', right_on='TEAM_Merge', how='left')

draft_with_games = draft_with_games[['Rank', 'Team', 'Player', 'School', 'DATE', 'TIME (ET)', 'AWAY', 'HOME']]

# Streamlit App
st.title("NBA Prospect Schedule")
st.header("Draft Board with Next Games")
st.dataframe(draft_with_games.drop_duplicates(subset=['Rank', 'Player', 'School']), hide_index=True)

# Prospect Distribution Visualization
school_summary = draft_df.groupby(['School'])['Player'].count().reset_index()
school_summary = school_summary.rename(columns={'School': 'School/Country', 'Player': 'Total'})
school_summary = school_summary.sort_values(by='Total', ascending=False)

fig, ax = plt.subplots(figsize=(12, 12))
cmap = plt.get_cmap("crest")
norm = plt.Normalize(school_summary['Total'].min(), school_summary['Total'].max())
colors = [cmap(norm(value)) for value in school_summary['Total']]

sns.barplot(data=school_summary, x="Total", y="School/Country", ax=ax, palette=colors)
ax.set_xlabel("Number of NBA Prospects")
ax.set_ylabel("School/Country")
st.header("NBA Prospect Distribution by School/Country")
st.pyplot(fig)
