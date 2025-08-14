import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from collections import defaultdict
import pytz

# Page config
st.set_page_config(
    page_title="Premier League 2024 Fixtures",
    page_icon="⚽",
    layout="wide"
)

# Title
st.title("⚽ Premier League Matches")

# Custom CSS for better styling and mobile responsiveness
st.markdown("""
<style>
.team-selector {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin: 10px 0;
}
.team-option {
    display: flex;
    align-items: center;
    padding: 8px 12px;
    border: 2px solid #ddd;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.3s;
    background: white;
}
.team-option:hover {
    border-color: #37003c;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
.team-option.selected {
    border-color: #37003c;
    background: #f8f9fa;
}
.team-option img {
    margin-right: 8px;
}

/* Mobile responsiveness */
@media (max-width: 768px) {
    .main > div {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    
    /* Responsive match display */
    .match-container {
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        text-align: center !important;
        padding: 10px !important;
        margin: 5px 0 !important;
    }
    
    .match-row {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 100% !important;
        margin: 5px 0 !important;
    }
    
    .team-name {
        font-size: 14px !important;
        margin: 0 8px !important;
    }
    
    .score {
        font-size: 18px !important;
        font-weight: bold !important;
        margin: 0 8px !important;
    }
    
    .match-info {
        font-size: 10px !important;
        margin-top: 5px !important;
    }
}

/* Center everything */
.stApp > div:first-child {
    max-width: 1000px;
    margin: 0 auto;
}
</style>
""", unsafe_allow_html=True)

def get_available_seasons():
    """Get available seasons including current year if after Aug 1"""
    current_date = datetime.now()
    current_year = current_date.year
    
    # Start with base seasons
    seasons = ["2024"]
    
    # Add current year if we're past August 1st
    if current_date.month >= 8 and str(current_year) not in seasons:
        seasons.append(str(current_year))
    
    return sorted(seasons, reverse=True)  # Most recent first

@st.cache_data
def fetch_matches(season):
    """Fetch Premier League matches from the API"""
    url = "https://sdp-prem-prod.premier-league-prod.pulselive.com/api/v2/matches"
    params = {
        "competition": "8",
        "season": season,
        "period": "FullTime",
        "_sort": "matchWeek:desc",
        "_limit": "400"  # Increased limit to get more matches
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])
    except requests.RequestException as e:
        st.error(f"Error fetching data: {e}")
        return []

def get_available_matchweeks(matches):
    """Get all available matchweeks from matches"""
    matchweeks = set()
    for match in matches:
        matchweeks.add(match["matchWeek"])
    return sorted(matchweeks, reverse=True)  # Most recent first

def fetch_match_stats(match_id):
    """Fetch match stats from the API"""
    url = f"https://sdp-prem-prod.premier-league-prod.pulselive.com/api/v3/matches/{match_id}/stats"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"Error fetching match stats: {e}")
        return None

def show_match_stats(match):
    match_id = match.get("matchId")
    stats_data = fetch_match_stats(match_id)
    if not stats_data or not isinstance(stats_data, list):
        st.error("No stats available for this match.")
        return
    # Parse home/away stats from list
    home_stats = next((item['stats'] for item in stats_data if item.get('side') == 'Home'), {})
    away_stats = next((item['stats'] for item in stats_data if item.get('side') == 'Away'), {})
    if not home_stats or not away_stats:
        st.error("Stats data format error.")
        return
    home_team = match["homeTeam"]
    away_team = match["awayTeam"]
    home_logo_url = f"https://resources.premierleague.com/premierleague25/badges/{home_team['id']}.svg"
    away_logo_url = f"https://resources.premierleague.com/premierleague25/badges/{away_team['id']}.svg"
    score_text = f"{home_team['score']} - {away_team['score']}"
    # Header with logos, names, score
    st.markdown(f"""
    <div style='display: flex; align-items: center; justify-content: center; gap: 32px; margin-bottom: 18px;'>
        <div style='text-align: right;'>
            <img src='{home_logo_url}' width='40' style='vertical-align: middle;'>
            <span style='font-weight: 600; font-size: 18px; margin-left: 8px;'>{home_team['name']}</span>
        </div>
        <div style='font-size: 28px; font-weight: bold; color: #37003c;'>{score_text}</div>
        <div style='text-align: left;'>
            <span style='font-weight: 600; font-size: 18px; margin-right: 8px;'>{away_team['name']}</span>
            <img src='{away_logo_url}' width='40' style='vertical-align: middle;'>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<h4 style='margin-top: 0;'>Top Stats</h4>", unsafe_allow_html=True)
    # Stat rows (order and keys updated)
    stat_rows = [
        ("xG", home_stats.get('expectedGoals', '-'), away_stats.get('expectedGoals', '-'), True),
        ("Total Shots", home_stats.get('totalScoringAtt', '-'), away_stats.get('totalScoringAtt', '-'), False),
        ("Shots On Target", home_stats.get('ontargetScoringAtt', '-'), away_stats.get('ontargetScoringAtt', '-'), False),
        ("Possession (%)", home_stats.get('possessionPercentage', '-'), away_stats.get('possessionPercentage', '-'), False),
        ("Passes", home_stats.get('totalPass', '-'), away_stats.get('totalPass', '-'), False),
        ("Corners", home_stats.get('cornerTaken', '-'), away_stats.get('cornerTaken', '-'), False),
        ("Saves", home_stats.get('saves', '-'), away_stats.get('saves', '-'), False),
        ("Big Chances", home_stats.get('bigChanceCreated', '-'), away_stats.get('bigChanceCreated', '-'), False),
    ]
    for stat, home_val, away_val, is_float in stat_rows:
        # Format values
        try:
            h_val = float(home_val)
            a_val = float(away_val)
            if not is_float:
                h_val_disp = str(int(round(h_val)))
                a_val_disp = str(int(round(a_val)))
            else:
                h_val_disp = f"{h_val:.2f}"
                a_val_disp = f"{a_val:.2f}"
        except:
            h_val_disp = home_val
            a_val_disp = away_val
        # Bold the higher value
        if h_val_disp != '-' and a_val_disp != '-':
            try:
                if float(h_val_disp) > float(a_val_disp):
                    h_val_disp = f"<b>{h_val_disp}</b>"
                elif float(a_val_disp) > float(h_val_disp):
                    a_val_disp = f"<b>{a_val_disp}</b>"
            except:
                pass
        st.markdown(f"""
        <div style='display: flex; justify-content: space-between; align-items: center; font-size: 15px; margin: 4px 0;'>
            <span style='color: #000;'>{h_val_disp}</span>
            <span style='color: #000; font-weight: 500;'>{stat}</span>
            <span style='color: #000;'>{a_val_disp}</span>
        </div>
        """, unsafe_allow_html=True)
    # Back button
    if st.button("Back to Fixtures", key="back_to_fixtures"):
        st.session_state.show_stats = False
        st.rerun()

def format_match_display(match):
    """Format a single match for display using Streamlit columns only, with smaller fonts and centered score"""
    home_team = match["homeTeam"]
    away_team = match["awayTeam"]
    kickoff_utc = datetime.strptime(match["kickoff"], "%Y-%m-%d %H:%M:%S")
    bst = pytz.timezone('Europe/London')
    kickoff_bst = bst.localize(kickoff_utc)
    formatted_date = kickoff_bst.strftime("%a %d %b")
    formatted_time = kickoff_bst.strftime("%H:%M")
    home_logo_url = f"https://resources.premierleague.com/premierleague25/badges/{home_team['id']}.svg"
    away_logo_url = f"https://resources.premierleague.com/premierleague25/badges/{away_team['id']}.svg"
    score_text = f"{home_team['score'] if match['period']=='FullTime' else '-'} - {away_team['score'] if match['period']=='FullTime' else '-'}"
    match_id = match.get("matchId")

    # Use columns for layout, mobile-friendly
    cols = st.columns([2, 1, 2])
    with cols[0]:
        st.markdown(f"<div style='display: flex; align-items: center; justify-content: flex-end;'>"
                    f"<span style='margin-right: 6px; font-weight: 500; font-size: 13px;'>{home_team['name']}</span>"
                    f"<img src='{home_logo_url}' width='22' height='22' style='margin-right: 4px;'>"
                    f"</div>", unsafe_allow_html=True)
    with cols[1]:
        st.markdown(f"<div style='text-align: center; font-size: 16px; font-weight: 600;'>{score_text}</div>", unsafe_allow_html=True)
    with cols[2]:
        st.markdown(f"<div style='display: flex; align-items: center;'>"
                    f"<img src='{away_logo_url}' width='22' height='22' style='margin-right: 4px;'>"
                    f"<span style='font-weight: 500; font-size: 13px;'>{away_team['name']}</span>"
                    f"</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='text-align: center; margin-top: 2px; color: gray; font-size: 11px;'>"
                f"{formatted_date} • {formatted_time} • {match['ground']} • {match['period']}"
                f"</div>", unsafe_allow_html=True)
    # Removed the View Stats button from here

def main():
    # Show stats page if selected
    if st.session_state.get("show_stats") and st.session_state.get("selected_match"):
        st.empty()  # Clear previous content
        show_match_stats(st.session_state.selected_match)
        return
    
    # Season selector
    available_seasons = get_available_seasons()
    selected_season = st.selectbox(
        "Select Season:",
        options=available_seasons,
        index=0  # Default to most recent season
    )
    
    # Fetch matches
    with st.spinner(f"Fetching Premier League {selected_season} season matches..."):
        matches = fetch_matches(selected_season)
    
    if not matches:
        st.error("No matches found or unable to fetch data.")
        return
    
    # Get available matchweeks
    available_matchweeks = get_available_matchweeks(matches)
    
    # Initialize session state for current matchweek
    if 'current_matchweek' not in st.session_state:
        st.session_state.current_matchweek = available_matchweeks[0]  # Start with most recent
    
    # Ensure current matchweek is still valid
    if st.session_state.current_matchweek not in available_matchweeks:
        st.session_state.current_matchweek = available_matchweeks[0]
    
    current_matchweek = st.session_state.current_matchweek
    current_index = available_matchweeks.index(current_matchweek)
    
    # Get matches for current matchweek
    current_week_matches = [match for match in matches if match["matchWeek"] == current_matchweek]
    
    # Get date range for the matchweek
    dates = [datetime.strptime(match["kickoff"], "%Y-%m-%d %H:%M:%S") for match in current_week_matches]
    min_date = min(dates).strftime("%d %b")
    max_date = max(dates).strftime("%d %b")
    
    # Matchweek navigation header with proper inline buttons
    col1, col2, col3 = st.columns([1, 6, 1])
    
    with col1:
        if current_index < len(available_matchweeks) - 1:
            if st.button("◀", key="prev_week", help="Previous matchweek"):
                st.session_state.current_matchweek = available_matchweeks[current_index + 1]
                st.rerun()
        else:
            st.markdown("<div style='text-align: center; color: #ccc; font-size: 24px; line-height: 50px;'>◀</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="background: #87CEEB; 
                    color: #333; 
                    padding: 8px 0; 
                    border-radius: 5px; 
                    margin: 10px 0;
                    text-align: center;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
            <h3 style="margin: 0; font-size: 18px; font-weight: bold;">Matchweek {current_matchweek}</h3>
            <p style="margin: 0; font-size: 11px; opacity: 0.8;">{min_date} - {max_date}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        if current_index > 0:
            if st.button("▶", key="next_week", help="Next matchweek"):
                st.session_state.current_matchweek = available_matchweeks[current_index - 1]
                st.rerun()
        else:
            st.markdown("<div style='text-align: center; color: #ccc; font-size: 24px; line-height: 50px;'>▶</div>", unsafe_allow_html=True)
    
    # Sort matches within the week by kickoff time
    current_week_matches.sort(key=lambda x: x["kickoff"])
    
    # Display each match
    for match in current_week_matches:
        format_match_display(match)
        match_id = match.get("matchId")
        if st.button(f"View Stats", key=f"stats_{match_id}"):
            st.session_state.selected_match = match
            st.session_state.show_stats = True
            st.rerun()

if __name__ == "__main__":
    main()
