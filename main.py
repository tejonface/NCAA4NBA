import streamlit as st
import bs4
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import date, timedelta

from seaborn import color_palette
from tabulate import tabulate


# Function to scrape NBA draft board tables
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
draft_url = "https://www.nbadraft.net/nba-mock-drafts/?year-mock=2025"
draft_df = scrape_nba_mock_draft(draft_url)
#print(draft_df)

# Function to scrape NCAA schedule
def scrape_ncaa_schedule():
    combined_df = pd.DataFrame()

    for i in range(7):  # Loop through the next 3 days
        single_date = date.today() + timedelta(days=0 + i)  # Start with today
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
            df.columns = [df.columns[0]] + [''] + list(df.columns[1:-1])  # Shift columns
            df["DATE"] = single_date
            combined_df = pd.concat([combined_df, df], ignore_index=True)

    return combined_df


# Scrape NCAA schedule
combined_df = scrape_ncaa_schedule()

#print(tabulate(combined_df, headers='keys', tablefmt='psql'))

# Rename columns
combined_df = combined_df.rename(columns={
    combined_df.columns[0]: "AWAY",
    combined_df.columns[1]: "HOME",
    combined_df.columns[2]: "TIME (ET)",
    combined_df.columns[3]: "TV",
    combined_df.columns[4]: "TICKETS",
    combined_df.columns[5]: "LOCATION",
    combined_df.columns[6]: "ODDS BY",
    combined_df.columns[7]: "DATE",
    "DATE": "DATE"
})


#Create duplicate column for cleaning and merging
#Clean Draft Board Schools

draft_df['School_Merge'] = draft_df['School']
draft_df['School_Merge'] = draft_df['School_Merge'].str.replace(r'St\.$', 'State', regex=True)
draft_df['School_Merge'] = draft_df['School_Merge'].str.replace(r'^St\.', 'Saint', regex=True)
draft_df['School_Merge'] = draft_df['School_Merge'].str.replace("'","")


# Create duplicate df to join on home or away team.
combined_df_home = combined_df.copy()
combined_df_away = combined_df.copy()

# Clean team names
combined_df_home['TEAM'] = combined_df_home['HOME'].str.replace(r'[@0-9]', '', regex=True).str.strip()
combined_df_away['TEAM'] = combined_df_away['AWAY'].str.replace(r'[@0-9]', '', regex=True).str.strip()

combined_df = pd.concat([combined_df_home, combined_df_away])

combined_df['TEAM'] = combined_df['TEAM'].str.replace("'","")
combined_df['TEAM'] = combined_df['TEAM'].str.replace(r'St\.$', 'State', regex=True)
combined_df['TEAM'] = combined_df['TEAM'].str.replace(r'^St\.', 'Saint', regex=True)


combined_df['HomeTeam'] = combined_df['HOME'].str.replace(r'[@0-9]', '', regex=True).str.strip()
combined_df['HomeTeam'] = combined_df['HomeTeam'].str.replace(r'St\.$', 'State', regex=True)
combined_df['HomeTeam'] = combined_df['HomeTeam'].str.replace(r'^St\.', 'Saint', regex=True)



combined_df['AwayTeam'] = combined_df['AWAY'].str.replace(r'[@0-9]', '', regex=True).str.strip()
combined_df['AwayTeam'] = combined_df['AwayTeam'].str.replace(r'St\.$', 'State', regex=True)
combined_df['AwayTeam'] = combined_df['AwayTeam'].str.replace(r'^St\.', 'Saint', regex=True)


#print(tabulate(combined_df))
#st.dataframe(combined_df)
# Merge draft board with upcoming games
upcoming_games_df = combined_df[combined_df['TEAM'].isin(draft_df['School_Merge'])]
draft_with_games = pd.merge(draft_df, upcoming_games_df, left_on='School_Merge', right_on='TEAM', how='left')

draft_with_games = draft_with_games[['Rank', 'Team', 'Player', 'School','DATE', 'TIME (ET)', 'AWAY', 'HOME', 'HomeTeam', 'AwayTeam']]

#print(tabulate(draft_with_games, headers='keys', tablefmt='psql'))

# Highlight matchups with NBA prospects on both teams
super_matchups = combined_df[
    (combined_df['HomeTeam'].isin(draft_df['School_Merge'])) & (combined_df['AwayTeam'].isin(draft_df['School_Merge']))]

super_matchups = super_matchups[['AWAY', 'HOME', 'DATE', 'TIME (ET)','HomeTeam', 'AwayTeam']].drop_duplicates()

#print(tabulate(super_matchups, headers='keys', tablefmt='psql'))
# Merge super_matchups with draft data to get players for each game
super_matchups_expanded = super_matchups.copy()

# Function to get players from a given school
def get_players_from_school(school):
    players = draft_df[draft_df['School'] == school][['Rank', 'Player', 'School']]
    return players.to_dict(orient='records')

# Add players from both home and away teams
super_matchups_expanded['HomeTeam_Players'] = super_matchups_expanded['HomeTeam'].apply(lambda x: get_players_from_school(x))
super_matchups_expanded['AwayTeam_Players'] = super_matchups_expanded['AwayTeam'].apply(lambda x: get_players_from_school(x))

# Combine home and away players into a single list
super_matchups_expanded['All_Players'] = super_matchups_expanded.apply(
    lambda row: row['HomeTeam_Players'] + row['AwayTeam_Players'], axis=1
)



# Sort players by rank before formatting and ensure alignment
super_matchups_expanded['All_Players'] = super_matchups_expanded.apply(
    lambda row: ', '.join([
        f"{p['School']}-#{str(p['Rank'])} {p['Player']}"
        for p in sorted(row['All_Players'], key=lambda x: int(x['Rank']))
    ]),
    axis=1
)

# Drop unnecessary columns and keep only the relevant details
super_matchups_expanded = super_matchups_expanded[['AWAY', 'HOME', 'DATE', 'TIME (ET)', 'All_Players']]

# Streamlit App
#st.set_page_config(layout="wide")
st.title("NBA Prospect Schedule")
st.text("Upcoming NCAA games featuring top 60 NBA draft prospects.")

with st.expander("More Information", expanded=False):
    st.text("This page helps basketball fans keep track of upcoming NCAA games featuring top prospects for the 2025 NBA Draft. If you don’t follow college basketball but want to know when the next potential stars are playing, this is your go-to schedule. Check back for updates on key matchups and players to watch.")

# Display full draft board with upcoming games
st.header("Draft Board with Next Games")
st.text("2025 NBA Mock Draft board with each NCAA players' upcoming game.")

draft_with_games = draft_with_games[['Rank', 'Team', 'Player', 'School','DATE', 'TIME (ET)', 'AWAY', 'HOME']]
st.dataframe(draft_with_games.drop_duplicates(subset=['Rank', 'Player', 'School']), hide_index=True)

# Display in Streamlit
st.header("SUPER MATCHUPS")
st.text("Games with top 60 NBA draft prospects on both teams.")
st.dataframe(super_matchups_expanded, hide_index=True)

# Get tomorrow's date as the default selection
tomorrow = date.today() + timedelta(days=1)

# Select a single date using segmented control, default to tomorrow
date_options = sorted(combined_df['DATE'].unique())
selected_date = st.segmented_control("Select Date", date_options, selection_mode="single", default=tomorrow)

# Display schedule for the selected date
st.header(f"Schedule for {selected_date}")

# Ensure selected_date is treated as a single value for filtering
if selected_date:
    # Filter upcoming games for the selected date
    filtered_games = upcoming_games_df[upcoming_games_df['DATE'] == selected_date]

    # Merge filtered games with draft data to add player info
    filtered_games_expanded = filtered_games.copy()

    # Function to get players for a team
    def get_players_from_school(school):
        return draft_df[draft_df['School'] == school][['Rank', 'Player', 'School']].to_dict(orient='records')

    # Get players from both home and away teams
    filtered_games_expanded['HomeTeam_Players'] = filtered_games_expanded['HomeTeam'].apply(lambda x: get_players_from_school(x))
    filtered_games_expanded['AwayTeam_Players'] = filtered_games_expanded['AwayTeam'].apply(lambda x: get_players_from_school(x))

    # Combine home and away players into a single list
    filtered_games_expanded['All_Players'] = filtered_games_expanded.apply(
        lambda row: row['HomeTeam_Players'] + row['AwayTeam_Players'], axis=1
    )

    # Sort players by rank before formatting
    filtered_games_expanded['All_Players'] = filtered_games_expanded.apply(
        lambda row: ', '.join([
            f"{p['School']}-#{str(p['Rank'])} {p['Player']}"
            for p in sorted(row['All_Players'], key=lambda x: int(x['Rank']))
        ]),
        axis=1
    )

    # Drop unnecessary columns and keep only relevant details
    filtered_games_expanded = filtered_games_expanded[['AWAY', 'HOME', 'DATE', 'TIME (ET)', 'All_Players']]

    # Display in Streamlit
    st.dataframe(filtered_games_expanded, hide_index=True)

else:
    st.write("Please select a date.")


school_summary = draft_df.groupby(['School'])['Player'].count()
school_summary =school_summary.reset_index()
school_summary = school_summary.rename(columns={'School':'School/Country','Player': 'Total'})
school_summary = school_summary.sort_values(by='Total', ascending=False)

import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

# Create a figure and axis
fig, ax = plt.subplots(figsize=(12, 12))
import seaborn as sns
import matplotlib.pyplot as plt



# Choose a colormap
cmap = plt.get_cmap("crest")

values = np.array(school_summary['Total'])

# Normalize values
norm = plt.Normalize(values.min(), values.max())

# Generate colors (same values get same colors)
colors = [cmap(norm(value)) for value in values]


# Create a bar plot of Schools with the most prospects
sns.barplot(
    data=school_summary,
    x="Total",
    y="School/Country",
    ax=ax,
    palette=colors

)

# Set labels and title
ax.set_xlabel("Number of NBA Prospects")
ax.set_ylabel("School/Country")
#ax.set_title("Schools with Most NBA Prospects in 2025 Draft")

# Rotate the labels for better readability if needed
plt.xticks(rotation=30)

# Display the plot in Streamlit
st.header("NBA Prospect Distribution by School/Country")
st.pyplot(fig)



col1, col2, col3 = st.columns(3)


with col1:
    st.header("Sources")
    url = "https://www.nbadraft.net/nba-mock-drafts/?year-mock=2025"
    st.write("[nbadraft.net mock draft board](%s)" % url)
    single_date = date.today() + timedelta(days=1)  # Start with tomorrow
    date_str = single_date.strftime("%Y%m%d")
    url = f"https://www.espn.com/mens-college-basketball/schedule/_/date/{date_str}"
    st.write("[espn.com ncaa schedule](%s)" % url)
    url = "https://www.jstew.info"
    st.write("[created by jstew.info](%s)" % url)

with col2:
    st.text("")

with col3:
    st.image("static/logo.png", width=200)
