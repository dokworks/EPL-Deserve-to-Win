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
st.title("⚽ Premier League 2024 Season Matches")

@st.cache_data
def fetch_matches():
    """Fetch Premier League matches from the API"""
    url = "https://sdp-prem-prod.premier-league-prod.pulselive.com/api/v2/matches"
    params = {
        "competition": "8",
        "season": "2024",
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
    # Fetch matches
    with st.spinner("Fetching Premier League matches..."):
        matches = fetch_matches()
    
    if not matches:
        st.error("No matches found or unable to fetch data.")
        return
    
    # Filter out PreMatch games
    completed_matches = [match for match in matches if match["period"] != "PreMatch"]
    
    if not completed_matches:
        st.warning("No completed matches found.")
        return
    
    # Group matches by matchweek
    matches_by_week = defaultdict(list)
    for match in completed_matches:
        matches_by_week[match["matchWeek"]].append(match)
    
    # Sort matchweeks in descending order (most current first)
    sorted_weeks = sorted(matches_by_week.keys(), reverse=True)
    
    # Display matches by matchweek
    for week in sorted_weeks:
        week_matches = matches_by_week[week]
        
        # Get date range for the matchweek
        dates = [datetime.strptime(match["kickoff"], "%Y-%m-%d %H:%M:%S") for match in week_matches]
        min_date = min(dates).strftime("%d %b")
        max_date = max(dates).strftime("%d %b")
        
        # Matchweek header
        st.markdown(f"""
        <div style="background: linear-gradient(90deg, #37003c, #00ff87); 
                    color: white; 
                    padding: 15px; 
                    border-radius: 10px; 
                    margin: 20px 0 10px 0;
                    text-align: center;">
            <h2 style="margin: 0; font-size: 24px;">Matchweek {week}</h2>
            <p style="margin: 5px 0 0 0; font-size: 14px;">{min_date} - {max_date}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Sort matches within the week by kickoff time
        week_matches.sort(key=lambda x: x["kickoff"])
        
        # Display each match
        for match in week_matches:
            format_match_display(match)
            st.markdown("<hr style='margin: 10px 0; border: 1px solid #eee;'>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
