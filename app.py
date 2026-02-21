"""
HackQuest MVP - Main Streamlit Application

This is the main entry point for the HackQuest gamified hackathon tracker.
Orchestrates authentication, quest progression, and UI rendering.

Validates: Requirements 1.5, 3.3, 3.4, 3.5, 4.3, 4.4, 4.5, 5.3, 5.4, 5.5,
           6.3, 6.4, 6.5, 11.1, 11.2, 12.1, 12.2, 12.4
"""

import copy
import logging
from datetime import datetime

import streamlit as st

from hackquest.auth import authenticate_team
from hackquest.database import PersistenceError, RateLimitError, update_team_quest
from hackquest.analytics import send_stage_metric
from hackquest.quests import QUESTS, validate_artifact, is_quest_unlocked
from hackquest.ui_components import (
    render_quest_card,
    render_profile,
    render_tavern,
    render_sidebar_auth
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="HackQuest MVP",
    page_icon="⚔️",
    layout="wide"
)


def initialize_session_state():
    """Initialize Streamlit session state with default values.
    
    Session state fields:
    - authenticated: bool - Whether team is logged in
    - team_name: str - Team's unique identifier
    - stage: int - Current unlocked quest (1-4)
    - xp: int - Total experience points
    - level: int - Calculated level (xp // 100)
    - idea_text: str | None - Quest 1 artifact
    - roles_text: str | None - Quest 2 artifact
    - github_link: str | None - Quest 3 artifact
    - pitch_link: str | None - Quest 4 artifact
    """
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "team_name" not in st.session_state:
        st.session_state.team_name = ""
    if "stage" not in st.session_state:
        st.session_state.stage = 1
    if "xp" not in st.session_state:
        st.session_state.xp = 0
    if "level" not in st.session_state:
        st.session_state.level = 0
    if "idea_text" not in st.session_state:
        st.session_state.idea_text = None
    if "roles_text" not in st.session_state:
        st.session_state.roles_text = None
    if "github_link" not in st.session_state:
        st.session_state.github_link = None
    if "pitch_link" not in st.session_state:
        st.session_state.pitch_link = None


def get_sheets_client():
    """Load Google Sheets client from Streamlit secrets.
    
    Returns:
        gspread worksheet object
        
    Raises:
        Exception: If secrets are not configured or connection fails
        
    Validates: Requirements 12.1, 12.2
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        
        # Load credentials from st.secrets
        credentials_dict = st.secrets["gcp_service_account"]
        
        # Create credentials object
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        credentials = Credentials.from_service_account_info(
            credentials_dict,
            scopes=scopes
        )
        
        # Create gspread client
        client = gspread.authorize(credentials)
        
        # Open the spreadsheet by ID
        spreadsheet_id = st.secrets["google_sheets_id"]
        spreadsheet = client.open_by_key(spreadsheet_id)
        
        # Get the first worksheet
        worksheet = spreadsheet.sheet1
        
        return worksheet
        
    except Exception as e:
        logger.error(f"Failed to connect to Google Sheets: {e}")
        raise


def get_datadog_api_key():
    """Load Datadog API key from Streamlit secrets.
    
    Returns:
        str: Datadog API key
        
    Raises:
        Exception: If secrets are not configured
        
    Validates: Requirements 12.1, 12.2
    """
    try:
        return st.secrets["datadog_api_key"]
    except Exception as e:
        logger.error(f"Failed to load Datadog API key: {e}")
        raise


def handle_authentication(sheets_client):
    """Handle team authentication from sidebar form submission.
    
    TEAM DATA ISOLATION: Only loads data for the authenticated team into session state.
    No cross-team data is accessible after authentication.
    
    Args:
        sheets_client: Google Sheets client
        
    Validates: Requirements 1.1, 1.2, 1.3, 1.5 (Team Data Isolation)
    """
    if "auth_submission" in st.session_state:
        auth_data = st.session_state["auth_submission"]
        team_name = auth_data.get("team_name", "").strip()
        pin = auth_data.get("pin", "").strip()
        
        # Clear the submission
        del st.session_state["auth_submission"]
        
        # Validate inputs
        if not team_name or not pin:
            st.sidebar.error("Please enter both team name and PIN")
            return
        
        # Attempt authentication
        try:
            team_data = authenticate_team(team_name, pin, sheets_client)
            
            if team_data is None:
                # Authentication failed
                st.sidebar.error("Invalid team name or PIN")
            else:
                # Authentication successful - load team data into session state
                # CRITICAL: Only load data for the authenticated team
                
                # Defensive check: Verify team_data is for the correct team
                assert team_data["team_name"] == team_name, \
                    f"Data isolation violation: Authenticated {team_data['team_name']} != requested {team_name}"
                
                st.session_state.authenticated = True
                st.session_state.team_name = team_data["team_name"]
                st.session_state.stage = team_data["stage"]
                st.session_state.xp = team_data["xp"]
                st.session_state.level = team_data["xp"] // 100
                st.session_state.idea_text = team_data["idea_text"]
                st.session_state.roles_text = team_data["roles_text"]
                st.session_state.github_link = team_data["github_link"]
                st.session_state.pitch_link = team_data["pitch_link"]
                
                st.sidebar.success(f"Welcome, {team_name}!")
                st.rerun()
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            st.sidebar.error("Unable to connect to database. Please try again.")


def handle_quest_submission(quest_number: int, sheets_client, datadog_api_key):
    """Handle quest artifact submission with validation, persistence, and XP award.
    
    Implements transaction rollback on persistence failure.
    
    Args:
        quest_number: Quest number (1-4)
        sheets_client: Google Sheets client
        datadog_api_key: Datadog API key
        
    Validates: Requirements 3.3, 3.4, 3.5, 4.3, 4.4, 4.5, 5.3, 5.4, 5.5,
               6.3, 6.4, 6.5, 11.1, 11.2
    """
    submission_key = f"quest_{quest_number}_submission"
    
    if submission_key in st.session_state:
        artifact = st.session_state[submission_key]
        
        # Clear the submission
        del st.session_state[submission_key]
        
        # Get quest configuration
        quest_config = QUESTS[quest_number - 1]
        
        # Validate artifact
        is_valid, error_message = validate_artifact(artifact)
        
        if not is_valid:
            st.error(error_message)
            return
        
        # Check if quest is unlocked
        if not is_quest_unlocked(st.session_state.stage, quest_number):
            st.error("This quest is locked. Complete previous quests first.")
            return
        
        # Save original state for rollback
        original_state = {
            "stage": st.session_state.stage,
            "xp": st.session_state.xp,
            "level": st.session_state.level,
            quest_config["artifact_field"]: st.session_state.get(quest_config["artifact_field"])
        }
        
        try:
            # Prepare quest data for persistence
            new_stage = st.session_state.stage + 1
            new_xp = st.session_state.xp + quest_config["xp_reward"]
            timestamp = datetime.utcnow().isoformat() + 'Z'
            
            quest_data = {
                "stage": new_stage,
                "xp": new_xp,
                "artifact_field": quest_config["artifact_field"],
                "artifact_value": artifact,
                "timestamp": timestamp
            }
            
            # Persist to database
            success = update_team_quest(
                st.session_state.team_name,
                quest_data,
                sheets_client
            )
            
            if not success:
                raise PersistenceError("Database write failed")
            
            # Update session state (optimistic update after successful persistence)
            st.session_state.stage = new_stage
            st.session_state.xp = new_xp
            st.session_state.level = new_xp // 100
            st.session_state[quest_config["artifact_field"]] = artifact
            
            # Send analytics metric (non-blocking)
            send_stage_metric(quest_config["stage_tag"], datadog_api_key)
            
            # Show success message
            st.success(f"✅ Quest {quest_number} completed! +{quest_config['xp_reward']} XP")
            st.balloons()
            st.rerun()
            
        except (PersistenceError, RateLimitError) as e:
            # Rollback session state
            st.session_state.stage = original_state["stage"]
            st.session_state.xp = original_state["xp"]
            st.session_state.level = original_state["level"]
            st.session_state[quest_config["artifact_field"]] = original_state[quest_config["artifact_field"]]
            
            # Display error message
            if isinstance(e, RateLimitError):
                st.error("System is busy. Please wait a moment and try again.")
            else:
                st.error("Unable to connect to database. Please try again.")
            
            logger.error(f"Quest submission failed for team {st.session_state.team_name}, quest {quest_number}: {e}")
            
        except Exception as e:
            # Rollback session state for unexpected errors
            st.session_state.stage = original_state["stage"]
            st.session_state.xp = original_state["xp"]
            st.session_state.level = original_state["level"]
            st.session_state[quest_config["artifact_field"]] = original_state[quest_config["artifact_field"]]
            
            st.error("An unexpected error occurred. Please contact support.")
            logger.error(f"Unexpected error in quest submission: {e}")


def main():
    """Main application entry point.
    
    Orchestrates:
    - Session state initialization
    - Sidebar authentication
    - Tab navigation (Tavern, Quest 1-4, Profile)
    - Quest submission handling
    """
    # Initialize session state
    initialize_session_state()
    
    # Display title
    st.title("⚔️ HackQuest MVP")
    
    # Load secrets and clients
    try:
        sheets_client = get_sheets_client()
        datadog_api_key = get_datadog_api_key()
    except Exception as e:
        st.error("Configuration error. Please contact the administrator.")
        logger.error(f"Failed to load configuration: {e}")
        return
    
    # Render sidebar authentication
    if not st.session_state.authenticated:
        render_sidebar_auth()
        handle_authentication(sheets_client)
        
        # Show welcome message
        st.info("👈 Please login or create a team using the sidebar to begin your quest!")
        
    else:
        # Display team info in sidebar
        st.sidebar.success(f"Logged in as: **{st.session_state.team_name}**")
        st.sidebar.metric("XP", f"{st.session_state.xp}")
        st.sidebar.metric("Level", st.session_state.level)
        st.sidebar.metric("Current Stage", st.session_state.stage)
        
        if st.sidebar.button("Logout"):
            # Clear session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        
        # Create tabs for navigation
        tabs = st.tabs(["🏰 Tavern", "⚔️ Quest 1", "🛡️ Quest 2", "🗡️ Quest 3", "🏆 Quest 4", "📜 Profile"])
        
        # Tavern tab
        with tabs[0]:
            render_tavern()
        
        # Quest tabs
        for i, quest in enumerate(QUESTS):
            with tabs[i + 1]:
                quest_number = quest["number"]
                is_unlocked = is_quest_unlocked(st.session_state.stage, quest_number)
                artifact_value = st.session_state.get(quest["artifact_field"])
                
                render_quest_card(
                    quest_number,
                    quest["title"],
                    quest["description"],
                    is_unlocked,
                    artifact_value
                )
                
                # Handle quest submission
                handle_quest_submission(quest_number, sheets_client, datadog_api_key)
        
        # Profile tab
        with tabs[5]:
            team_data = {
                "team_name": st.session_state.team_name,
                "xp": st.session_state.xp,
                "stage": st.session_state.stage,
                "idea_text": st.session_state.idea_text,
                "roles_text": st.session_state.roles_text,
                "github_link": st.session_state.github_link,
                "pitch_link": st.session_state.pitch_link
            }
            render_profile(team_data)


if __name__ == "__main__":
    main()
