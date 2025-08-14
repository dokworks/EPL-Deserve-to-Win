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

# Custom CSS for better styling
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
    """Format a single match for display"""
    home_team = match["homeTeam"]
    away_team = match["awayTeam"]
    
    # Parse the kickoff time and convert to local timezone
    kickoff_utc = datetime.strptime(match["kickoff"], "%Y-%m-%d %H:%M:%S")
    # The API returns BST time, so we need to handle timezone properly
    bst = pytz.timezone('Europe/London')
    kickoff_bst = bst.localize(kickoff_utc)
    
    # Display in local timezone using JavaScript for browser timezone detection
    formatted_date = kickoff_bst.strftime("%a %d %b")
    formatted_time = kickoff_bst.strftime("%H:%M")
    iso_time = kickoff_bst.isoformat()
    
    # Team logos
    home_logo_url = f"https://resources.premierleague.com/premierleague25/badges/{home_team['id']}.svg"
    away_logo_url = f"https://resources.premierleague.com/premierleague25/badges/{away_team['id']}.svg"
    
    # Create columns for the match display
    col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 2])
    
    with col1:
        st.markdown(f"""
        <div style="display: flex; align-items: center; justify-content: flex-end;">
            <span style="margin-right: 10px; font-weight: bold;">{home_team['name']}</span>
            <img src="{home_logo_url}" width="30" height="30" style="margin-right: 5px;">
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if match["period"] == "FullTime":
            st.markdown(f"<div style='text-align: center; font-size: 24px; font-weight: bold;'>{home_team['score']}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='text-align: center;'>-</div>", unsafe_allow_html=True)
    
    with col3:
        st.markdown("<div style='text-align: center; font-size: 20px;'>-</div>", unsafe_allow_html=True)
    
    with col4:
        if match["period"] == "FullTime":
            st.markdown(f"<div style='text-align: center; font-size: 24px; font-weight: bold;'>{away_team['score']}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='text-align: center;'>-</div>", unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
        <div style="display: flex; align-items: center;">
            <img src="{away_logo_url}" width="30" height="30" style="margin-right: 10px;">
            <span style="font-weight: bold;">{away_team['name']}</span>
        </div>
        """, unsafe_allow_html=True)
    
    # Additional match info with JavaScript for local time conversion
    st.markdown(f"""
    <div style="text-align: center; margin-top: 5px; color: gray; font-size: 12px;">
        <span id="date-{match['matchId']}">{formatted_date}</span> • 
        <span id="time-{match['matchId']}">{formatted_time}</span> • 
        {match['ground']} • {match['period']}
    </div>
    <script>
        (function() {{
            var isoTime = "{iso_time}";
            var localDate = new Date(isoTime);
            var options = {{ weekday: 'short', day: '2-digit', month: 'short' }};
            var timeOptions = {{ hour: '2-digit', minute: '2-digit', hour12: false }};
            
            var dateElement = document.getElementById('date-{match['matchId']}');
            var timeElement = document.getElementById('time-{match['matchId']}');
            
            if (dateElement) dateElement.textContent = localDate.toLocaleDateString('en-GB', options);
            if (timeElement) timeElement.textContent = localDate.toLocaleTimeString('en-GB', timeOptions);
        }})();
    </script>
    """, unsafe_allow_html=True)

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
    
    # Matchweek navigation header
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col1:
        # Left arrow (previous matchweek - lower number)
        if current_index < len(available_matchweeks) - 1:
            if st.button("◀", key="prev_week", help="Previous matchweek"):
                st.session_state.current_matchweek = available_matchweeks[current_index + 1]
                st.rerun()
        else:
            st.markdown("<div style='text-align: center; color: #ccc; font-size: 24px;'>◀</div>", unsafe_allow_html=True)
    
    with col2:
        # Matchweek header - back to original style with green gradient
        st.markdown(f"""
        <div style="background: linear-gradient(90deg, #37003c, #00ff87); 
                    color: white; 
                    padding: 15px; 
                    border-radius: 10px; 
                    margin: 20px 0 10px 0;
                    text-align: center;">
            <h2 style="margin: 0; font-size: 24px;">Matchweek {current_matchweek}</h2>
            <p style="margin: 5px 0 0 0; font-size: 14px;">{min_date} - {max_date}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # Right arrow (next matchweek - higher number)
        if current_index > 0:
            if st.button("▶", key="next_week", help="Next matchweek"):
                st.session_state.current_matchweek = available_matchweeks[current_index - 1]
                st.rerun()
        else:
            st.markdown("<div style='text-align: center; color: #ccc; font-size: 24px;'>▶</div>", unsafe_allow_html=True)
    
    # Sort matches within the week by kickoff time
    current_week_matches.sort(key=lambda x: x["kickoff"])
    
    # Display each match
    for match in current_week_matches:
        format_match_display(match)
        st.markdown("<hr style='margin: 10px 0; border: 1px solid #eee;'>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
