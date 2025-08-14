import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import re
from typing import Any, Dict, List
import pytz
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(
    page_title="Premier League Fixtures Analysis",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
STATS_URL = "https://sdp-prem-prod.premier-league-prod.pulselive.com/api/v2/competitions/8/teams/stats/leaderboard"
MATCHES_URL = "https://sdp-prem-prod.premier-league-prod.pulselive.com/api/v2/matches"
TEAM_LOGO_URL = "https://resources.premierleague.com/premierleague25/badges/{team_id}.svg"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://www.premierleague.com",
    "Referer": "https://www.premierleague.com/fixtures",
    "Accept": "application/json",
    "Accept-Language": "en-GB,en;q=0.9",
}

# Cache functions to avoid repeated API calls
@st.cache_data(ttl=3600)  # Cache for 1 hour
def http_get(url: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Make HTTP GET request with retry logic"""
    for i in range(5):
        try:
            r = requests.get(url, params=params or {}, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(min(2 ** i, 8))
                continue
            try:
                body = r.json()
            except Exception:
                body = r.text[:500]
            st.error(f"HTTP {r.status_code} {url} params={params} body={body}")
            return {}
        except Exception as e:
            if i == 4:  # Last retry
                st.error(f"Failed to fetch data: {str(e)}")
                return {}
            time.sleep(min(2 ** i, 8))
    return {}

def norm_name(s: str) -> str:
    """Normalize team names for matching"""
    if not s:
        return ""
    _name_rx = re.compile(r"[^a-z0-9]+")
    return _name_rx.sub("", s.lower())

@st.cache_data(ttl=3600)
def fetch_stats(season: str = "2024", limit: int = 40) -> pd.DataFrame:
    """Fetch team statistics"""
    params = {"_sort": "total_shots:desc", "season": season, "_limit": str(limit)}
    payload = http_get(STATS_URL, params)
    
    if not payload:
        return pd.DataFrame()
    
    rows = []
    for row in payload.get("data", []):
        tm = row.get("teamMetadata", {}) or {}
        s = row.get("stats", {}) or {}
        team_name = tm.get("name")
        sot = float(s.get("shotsOnTargetIncGoals", 0) or 0)
        cin = float(s.get("shotsOnConcededInsideBox", 0) or 0)
        cout = float(s.get("shotsOnConcededOutsideBox", 0) or 0)
        denom = sot + cin + cout
        metric = (sot / denom) if denom > 0 else np.nan
        rows.append({
            "team": team_name,
            "team_norm": norm_name(team_name),
            "metric": metric,
            "metric_%": None if pd.isna(metric) else round(metric * 100, 2),
        })
    
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.dropna(subset=["team_norm"]).drop_duplicates(subset=["team_norm"]).reset_index(drop=True)
    return df

@st.cache_data(ttl=1800)  # Cache for 30 minutes
def fetch_matches(season: str = "2025", page_size: int = 50) -> pd.DataFrame:
    """Fetch match fixtures"""
    params = {"competition": "8", "season": season, "_limit": str(page_size)}
    items: List[Dict[str, Any]] = []
    
    while True:
        payload = http_get(MATCHES_URL, params)
        if not payload:
            break
        items.extend(payload.get("data", []) or [])
        nxt = payload.get("pagination", {}).get("_next")
        if not nxt:
            break
        params["_next"] = nxt

    rows = []
    for m in items:
        home = m.get("homeTeam", {}) or {}
        away = m.get("awayTeam", {}) or {}
        
        # Get scores if available
        home_score = None
        away_score = None
        if m.get("score"):
            home_score = m.get("score", {}).get("home")
            away_score = m.get("score", {}).get("away")
        
        rows.append({
            "matchId": m.get("matchId"),
            "matchWeek": m.get("matchWeek"),
            "period": m.get("period"),
            "kickoff": m.get("kickoff"),
            "ground": m.get("ground"),
            "Home Team": home.get("name"),
            "Away Team": away.get("name"),
            "homeScore": home_score,
            "awayScore": away_score,
            "home_norm": norm_name(home.get("name")),
            "away_norm": norm_name(away.get("name")),
        })
    
    df = pd.DataFrame(rows)
    if not df.empty:
        df["kickoff_dt"] = pd.to_datetime(df["kickoff"], errors="coerce", utc=True)
        df = df.sort_values(["kickoff_dt", "matchWeek", "matchId"], na_position="last").reset_index(drop=True)
    return df

def convert_to_melbourne_time(df: pd.DataFrame) -> pd.DataFrame:
    """Convert kickoff times to Melbourne timezone"""
    if df.empty or 'kickoff' not in df.columns:
        return df
    
    melbourne_tz = pytz.timezone('Australia/Melbourne')
    df = df.copy()
    df['kickoff_utc'] = pd.to_datetime(df['kickoff'], errors='coerce', utc=True)
    
    # Apply 1-hour correction as determined in the notebook
    df['kickoff_utc_corrected'] = df['kickoff_utc'] - timedelta(hours=1)
    df['kickoff_melbourne'] = df['kickoff_utc_corrected'].dt.tz_convert(melbourne_tz)
    df['kickoff_formatted'] = df['kickoff_melbourne'].dt.strftime('%Y-%m-%d %H:%M %Z')
    
    return df

@st.cache_data(ttl=3600)
def get_team_ids_mapping() -> Dict[str, str]:
    """Create a mapping of team names to team IDs for logo URLs"""
    # Premier League 2024-25 season team IDs based on official resources
    team_id_map = {
        'Arsenal': '1',
        'Aston Villa': '2',
        'Bournemouth': '91',
        'AFC Bournemouth': '91',
        'Brentford': '94',
        'Brighton & Hove Albion': '36',
        'Brighton': '36',
        'Chelsea': '4',
        'Crystal Palace': '31',
        'Everton': '7',
        'Fulham': '34',
        'Ipswich Town': '40',
        'Leicester City': '13',
        'Liverpool': '10',
        'Manchester City': '11',
        'Manchester United': '12',
        'Newcastle United': '23',
        'Nottingham Forest': '17',
        'Southampton': '20',
        'Tottenham Hotspur': '21',
        'Tottenham': '21',
        'West Ham United': '25',
        'West Ham': '25',
        'Wolverhampton Wanderers': '38',
        'Wolves': '38',
        # Backup/alternative names
        'Man City': '11',
        'Man United': '12',
        'Man Utd': '12',
        'Spurs': '21',
    }
    return team_id_map

def get_team_logo_url(team_name: str, team_id_map: Dict[str, str]) -> str:
    """Get the logo URL for a team"""
    team_id = team_id_map.get(team_name, '1')  # Default to Arsenal if not found
    return TEAM_LOGO_URL.format(team_id=team_id)

def display_matches_by_matchweek(matches_df: pd.DataFrame, season: str = "2024"):
    """Display matches grouped by matchweek with team logos and scores"""
    if matches_df.empty:
        st.warning("No matches found")
        return
    
    # Filter out PreMatch period matches
    filtered_matches = matches_df[matches_df['period'] != 'PreMatch'].copy()
    
    if filtered_matches.empty:
        st.warning("No completed or live matches found (excluding PreMatch)")
        return
    
    # Get team ID mapping for logos
    team_id_map = get_team_ids_mapping()
    
    # Group by matchweek
    for matchweek in sorted(filtered_matches['matchWeek'].dropna().unique()):
        week_matches = filtered_matches[filtered_matches['matchWeek'] == matchweek]
        
        st.subheader(f"Matchweek {int(matchweek)}")
        
        # Create columns for each match in the week
        if len(week_matches) > 0:
            # Display matches in a more visual format
            for _, match in week_matches.iterrows():
                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 2])
                
                home_team = match['Home Team']
                away_team = match['Away Team']
                
                with col1:
                    # Home team with logo
                    home_logo_url = get_team_logo_url(home_team, team_id_map)
                    st.markdown(f"""
                        <div style="display: flex; align-items: center; justify-content: flex-end;">
                            <span style="margin-right: 10px; font-weight: bold;">{home_team}</span>
                            <img src="{home_logo_url}" width="30" height="30" style="object-fit: contain;">
                        </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    # Home score (if available)
                    home_score = match.get('homeScore', '-')
                    st.markdown(f"<div style='text-align: center; font-size: 24px; font-weight: bold;'>{home_score}</div>", unsafe_allow_html=True)
                
                with col3:
                    # VS separator
                    st.markdown("<div style='text-align: center; font-size: 16px;'>vs</div>", unsafe_allow_html=True)
                
                with col4:
                    # Away score (if available)
                    away_score = match.get('awayScore', '-')
                    st.markdown(f"<div style='text-align: center; font-size: 24px; font-weight: bold;'>{away_score}</div>", unsafe_allow_html=True)
                
                with col5:
                    # Away team with logo
                    away_logo_url = get_team_logo_url(away_team, team_id_map)
                    st.markdown(f"""
                        <div style="display: flex; align-items: center; justify-content: flex-start;">
                            <img src="{away_logo_url}" width="30" height="30" style="object-fit: contain; margin-right: 10px;">
                            <span style="font-weight: bold;">{away_team}</span>
                        </div>
                    """, unsafe_allow_html=True)
                
                # Match details
                kickoff_time = match.get('kickoff_formatted', match.get('kickoff', 'TBD'))
                period = match.get('period', 'Unknown')
                ground = match.get('ground', 'Unknown')
                
                st.markdown(f"""
                    <div style="text-align: center; font-size: 12px; color: gray; margin: 5px 0;">
                        {kickoff_time} | {period} | {ground}
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown("---")
        
        st.markdown("<br>", unsafe_allow_html=True)

def build_schedule_with_metrics(stats_df: pd.DataFrame, matches_df: pd.DataFrame, prematch_only: bool = True) -> pd.DataFrame:
    """Build schedule with team metrics and xGDiff calculation"""
    if matches_df.empty:
        return pd.DataFrame()
    
    if prematch_only and "period" in matches_df.columns:
        matches_df = matches_df[matches_df["period"] == "PreMatch"].copy()

    # Map normalized team name -> metric/percent
    metric_by_name = dict(zip(stats_df["team_norm"], stats_df["metric"]))
    pct_by_name = dict(zip(stats_df["team_norm"], stats_df["metric_%"]))

    out = matches_df.copy()
    out["Home Team %"] = out["home_norm"].map(pct_by_name)
    out["Away Team %"] = out["away_norm"].map(pct_by_name)
    out["home_metric"] = out["home_norm"].map(metric_by_name).astype(float)
    out["away_metric"] = out["away_norm"].map(metric_by_name).astype(float)

    # xGDiff calculation
    out["xGDiff"] = (out["home_metric"] * 5.0) + (out["away_metric"] * -4.6)

    # Round values
    out["Home Team %"] = out["Home Team %"].round(2)
    out["Away Team %"] = out["Away Team %"].round(2)
    out["xGDiff"] = out["xGDiff"].round(3)

    return out

def main():
    # Header
    st.title("⚽ Premier League Fixtures Analysis")
    st.markdown("Analysis of Premier League fixtures with team statistics and Expected Goal Difference (xGDiff)")

    # Create tabs
    tab1, tab2 = st.tabs(["📊 Fixtures Analysis", "📅 Matches by Matchweek"])

    # Sidebar controls
    st.sidebar.header("Settings")
    stats_season = st.sidebar.selectbox("Stats Season", ["2025", "2024"], index=0)
    fixtures_season = st.sidebar.selectbox("Fixtures Season", ["2025", "2024"], index=0)
    
    # Add refresh button
    if st.sidebar.button("Refresh Data"):
        st.cache_data.clear()
        st.rerun()

def main():
    # Header
    st.title("⚽ Premier League Fixtures Analysis")
    st.markdown("Analysis of Premier League fixtures with team statistics and Expected Goal Difference (xGDiff)")

    # Create tabs
    tab1, tab2 = st.tabs(["📊 Fixtures Analysis", "📅 Matches by Matchweek"])

    # Sidebar controls
    st.sidebar.header("Settings")
    stats_season = st.sidebar.selectbox("Stats Season", ["2025", "2024"], index=0)
    fixtures_season = st.sidebar.selectbox("Fixtures Season", ["2025", "2024"], index=0)
    
    # Add refresh button
    if st.sidebar.button("Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    # Load data (shared between tabs)
    with st.spinner("Fetching team statistics..."):
        stats_df = fetch_stats(season=stats_season, limit=40)
    
    if stats_df.empty:
        st.error("Failed to fetch team statistics")
        return

    with st.spinner("Fetching fixtures..."):
        matches_df = fetch_matches(season=fixtures_season, page_size=50)
    
    if matches_df.empty:
        st.error("Failed to fetch fixtures")
        return

    # Convert to Melbourne time
    matches_df = convert_to_melbourne_time(matches_df)

    # Tab 1: Fixtures Analysis
    with tab1:
        prematch_only = st.checkbox("PreMatch fixtures only", value=True)
        match_limit = st.number_input("Match limit", min_value=1, max_value=100, value=20)
        
        # Apply match limit
        limited_matches_df = matches_df.copy()
        if match_limit and not limited_matches_df.empty:
            limited_matches_df = limited_matches_df.head(match_limit)

        # Build schedule
        schedule = build_schedule_with_metrics(stats_df, limited_matches_df, prematch_only=prematch_only)

        if schedule.empty:
            st.warning("No matches found with the current filters")
        else:
            # Update schedule with Melbourne time
            if 'kickoff_formatted' in limited_matches_df.columns:
                kickoff_mapping = dict(zip(limited_matches_df.index, limited_matches_df['kickoff_formatted']))
                if len(schedule) <= len(limited_matches_df):
                    schedule['Kickoff Melbourne'] = schedule.index.map(kickoff_mapping)
                    schedule = schedule.drop('kickoff', axis=1, errors='ignore')
                    schedule = schedule.rename(columns={'Kickoff Melbourne': 'Kickoff'})

            # Display metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Teams Loaded", len(stats_df))
            with col2:
                st.metric("Total Fixtures", len(matches_df))
            with col3:
                st.metric("Fixtures Shown", len(schedule))
            with col4:
                missing_count = schedule[["Home Team %", "Away Team %"]].isna().any(axis=1).sum()
                st.metric("Missing Stats", missing_count)

            # Main table
            st.header("Fixtures with Analysis")
            
            # Prepare display columns
            display_cols = ["Home Team", "Home Team %", "Away Team", "Away Team %", "xGDiff", "matchWeek", "Kickoff", "ground"]
            display_schedule = schedule[display_cols].rename(columns={"matchWeek": "Week", "ground": "Ground"})
            
            # Style the dataframe
            def style_xgdiff(val):
                if pd.isna(val):
                    return ''
                color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
                return f'color: {color}; font-weight: bold'

            styled_schedule = display_schedule.style.applymap(style_xgdiff, subset=['xGDiff'])
            st.dataframe(styled_schedule, use_container_width=True)

            # Missing stats warning
            missing = schedule[schedule[["Home Team %", "Away Team %"]].isna().any(axis=1)]
            if not missing.empty:
                st.warning(f"⚠️ {len(missing)} fixtures have missing team statistics")
                with st.expander("View fixtures with missing stats"):
                    st.dataframe(missing[["Home Team", "Away Team", "matchWeek", "Kickoff", "ground"]], use_container_width=True)

            # Download option
            csv = display_schedule.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"premier_league_fixtures_{fixtures_season}.csv",
                mime="text/csv"
            )

    # Tab 2: Matches by Matchweek
    with tab2:
        st.header(f"Season {fixtures_season} - Matches by Matchweek")
        st.markdown("*Showing all periods except PreMatch*")
        display_matches_by_matchweek(matches_df, fixtures_season)

    # Footer info (in sidebar)
    st.sidebar.markdown("---")
    st.sidebar.markdown("**xGDiff Calculation:**")
    st.sidebar.markdown("(Home Team % × 5) + (Away Team % × -4.6)")
    st.sidebar.markdown("**Times:** Melbourne timezone with 1-hour API correction")
    
    # Show current Melbourne time
    melbourne_tz = pytz.timezone('Australia/Melbourne')
    current_time = datetime.now(melbourne_tz)
    st.sidebar.markdown(f"**Current Melbourne Time:** {current_time.strftime('%Y-%m-%d %H:%M %Z')}")

    # Matchweek display
    st.sidebar.markdown("---")
    st.sidebar.header("Matchweek Display")
    if st.sidebar.button("Show Matches by Matchweek"):
        display_matches_by_matchweek(matches_df, season=fixtures_season)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        st.error("Please check the logs or contact support if this persists.")
        st.stop()
