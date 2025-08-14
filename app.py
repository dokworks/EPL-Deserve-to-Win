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

def format_match_display(match):
    """Format a single match for display using Streamlit columns only, with smaller fonts and centered score, and kickoff date/time"""
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

    # Use columns for layout, mobile-friendly
    cols = st.columns([2, 1, 2])
    with cols[0]:
        st.markdown(f"<div style='display: flex; align-items: center; justify-content: flex-end;'>"
                    f"<span style='margin-right: 6px; font-weight: 500; font-size: 13px;'>{home_team['name']}</span>"
                    f"<img src='{home_logo_url}' width='22' height='22' style='margin-right: 4px;'>"
                    f"</div>", unsafe_allow_html=True)
    with cols[1]:
        st.markdown(f"<div style='text-align: center; font-size: 13px; color: #555; margin-bottom: 2px;'>{formatted_date}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align: center; font-size: 16px; font-weight: 600;'>{score_text}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align: center; font-size: 12px; color: #888; margin-top: 2px;'>{formatted_time}</div>", unsafe_allow_html=True)
    with cols[2]:
        st.markdown(f"<div style='display: flex; align-items: center;'>"
                    f"<img src='{away_logo_url}' width='22' height='22' style='margin-right: 4px;'>"
                    f"<span style='font-weight: 500; font-size: 13px;'>{away_team['name']}</span>"
                    f"</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='text-align: center; margin-top: 2px; color: gray; font-size: 11px;'>"
                f"{match['ground']} • {match['period']}"
                f"</div>", unsafe_allow_html=True)

def main():
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

if __name__ == "__main__":
    main()
