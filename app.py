import streamlit as st
import soccerdata as sd
import pandas as pd
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Premier League Fixtures (Understat)",
    page_icon="⚽",
    layout="wide"
)

st.title("⚽ Premier League Matches (Understat)")

# Select season
current_year = datetime.now().year
current_month = datetime.now().month
seasons = ["2024/25"]
if current_month >= 8:
    seasons.append("2025/26")
selected_season = st.selectbox("Select Season:", options=seasons, index=0)

# Map season string to Understat format
season_map = {"2024/25": "2425", "2025/26": "2526"}
understat_season = season_map[selected_season]

# Load Understat EPL data
understat = sd.Understat(leagues="ENG-Premier League", seasons=understat_season)
team_match_stats = understat.read_team_match_stats()

# Sort by date desc
team_match_stats = team_match_stats.sort_values("date", ascending=False)

# Display matches
for idx, row in team_match_stats.iterrows():
    home = row["home_team"]
    away = row["away_team"]
    home_code = row["home_team_code"]
    away_code = row["away_team_code"]
    date_str = pd.to_datetime(row["date"]).strftime("%a %d %b %Y %H:%M")
    score = f"{row['home_goals']} - {row['away_goals']}"
    home_xg = row["home_xg"]
    away_xg = row["away_xg"]
    st.markdown(f"""
    <div style='display: flex; align-items: center; justify-content: center; gap: 18px; margin-bottom: 10px;'>
        <span style='font-weight: 600; font-size: 15px;'>{date_str}</span>
        <span style='font-weight: 500; font-size: 15px;'>{home} ({home_code})</span>
        <span style='font-size: 18px; font-weight: bold;'>{score}</span>
        <span style='font-weight: 500; font-size: 15px;'>{away} ({away_code})</span>
        <span style='font-size: 13px; color: #888;'>xG: {home_xg:.2f} - {away_xg:.2f}</span>
    </div>
    """, unsafe_allow_html=True)
