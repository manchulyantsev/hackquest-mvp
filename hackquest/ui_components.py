"""UI components module for HackQuest MVP.

This module provides Streamlit UI rendering functions for all application views:
- Quest cards with lock state and submission forms
- Profile display with XP, level, and artifacts
- Tavern information hub
- Sidebar authentication form

Validates: Requirements 7.1, 7.2, 7.4, 7.5, 8.1, 8.2, 8.3, 8.4, 13.1, 13.2, 13.3, 13.4
"""

import streamlit as st
from hackquest.quests import calculate_level


def render_quest_card(
    quest_number: int,
    title: str,
    description: str,
    is_unlocked: bool,
    artifact_value: str | None
) -> None:
    """Render a quest card with lock state and submission form.
    
    Displays:
    - Quest title and description
    - Lock state indicator (locked/unlocked)
    - Submission form with text area (if unlocked)
    - Submitted artifact display (if already submitted)
    
    Args:
        quest_number: Quest number (1-4)
        title: Quest title
        description: Quest description
        is_unlocked: Whether the quest is unlocked
        artifact_value: Previously submitted artifact (None if not submitted)
        
    Returns:
        None (renders UI directly via Streamlit)
        
    Validates:
        - Requirements 7.1 (quest card rendering)
        - Requirements 13.1, 13.2, 13.3, 13.4 (UI navigation)
    """
    st.subheader(f"Quest {quest_number}: {title}")
    st.write(description)
    
    if not is_unlocked:
        # Display locked state
        st.warning("🔒 This quest is locked. Complete previous quests to unlock.")
        st.info("Complete the previous quest to unlock this one!")
    elif artifact_value:
        # Display submitted artifact
        st.success("✅ Quest completed!")
        st.text_area(
            "Your submission:",
            value=artifact_value,
            height=100,
            disabled=True,
            key=f"quest_{quest_number}_display"
        )
    else:
        # Display submission form
        st.info("📝 This quest is unlocked! Submit your artifact below.")
        
        with st.form(key=f"quest_{quest_number}_form"):
            artifact_input = st.text_area(
                "Enter your artifact (1-1000 characters):",
                height=150,
                max_chars=1000,
                key=f"quest_{quest_number}_input"
            )
            
            submit_button = st.form_submit_button("Submit Quest")
            
            if submit_button:
                # Store submission in session state for processing by main app
                st.session_state[f"quest_{quest_number}_submission"] = artifact_input


def render_profile(team_data: dict) -> None:
    """Render profile tab displaying team progress and artifacts.
    
    Displays:
    - Team name
    - Current XP and level
    - All four artifacts (with pending status for unsubmitted ones)
    
    Args:
        team_data: Team data dict containing:
            - team_name: str
            - xp: int
            - stage: int
            - idea_text: str | None
            - roles_text: str | None
            - github_link: str | None
            - pitch_link: str | None
            
    Returns:
        None (renders UI directly via Streamlit)
        
    Validates:
        - Requirements 7.1, 7.2, 7.4, 7.5 (profile display)
    """
    st.header("⚔️ Character Sheet")
    
    # Display team name
    st.subheader(f"Team: {team_data.get('team_name', 'Unknown')}")
    
    # Display XP and level
    xp = team_data.get('xp', 0)
    level = calculate_level(xp)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Experience Points", f"{xp} XP")
    with col2:
        st.metric("Level", level)
    
    st.divider()
    
    # Display artifacts
    st.subheader("📜 Quest Artifacts")
    
    artifacts = [
        ("Quest 1: The Call to Adventure", "idea_text", "Idea"),
        ("Quest 2: Gathering the Party", "roles_text", "Team Roles"),
        ("Quest 3: The Road of Trials", "github_link", "GitHub Repository"),
        ("Quest 4: The Return", "pitch_link", "Presentation")
    ]
    
    for quest_title, field_name, artifact_name in artifacts:
        artifact_value = team_data.get(field_name)
        
        st.write(f"**{quest_title}**")
        
        if artifact_value:
            # Display submitted artifact
            st.text_area(
                f"{artifact_name}:",
                value=artifact_value,
                height=80,
                disabled=True,
                key=f"profile_{field_name}"
            )
        else:
            # Display pending status
            st.info(f"⏳ {artifact_name}: Pending submission")
        
        st.write("")  # Add spacing


def render_tavern() -> None:
    """Render tavern tab with hackathon information and quest mechanics.
    
    Displays:
    - Hackathon overview
    - Quest mechanics explanation
    - XP and leveling system details
    
    Returns:
        None (renders UI directly via Streamlit)
        
    Validates:
        - Requirements 8.1, 8.2, 8.3, 8.4 (tavern information hub)
    """
    st.header("🏰 The Tavern")
    
    st.markdown("""
    Welcome, brave adventurer! You've entered the **HackQuest Tavern**, 
    where your hackathon journey begins.
    """)
    
    st.divider()
    
    # Hackathon overview
    st.subheader("📖 About the Hackathon")
    st.markdown("""
    HackQuest transforms your hackathon experience into an epic adventure! 
    Progress through four sequential quests, earn experience points, and 
    level up as you build your project from idea to presentation.
    
    This gamified system helps you:
    - Stay organized with structured milestones
    - Track your progress visually
    - Celebrate achievements along the way
    """)
    
    st.divider()
    
    # Quest mechanics
    st.subheader("⚔️ Quest Mechanics")
    st.markdown("""
    **How Quests Work:**
    
    1. **Sequential Unlocking**: Complete quests in order. Each quest unlocks the next.
    2. **Artifact Submission**: Submit your work (text, links) to complete each quest.
    3. **Validation**: Artifacts must be 1-1000 characters long.
    4. **Progression**: Once submitted, you can't change artifacts (choose wisely!).
    
    **The Four Quests:**
    
    - **Quest 1: The Call to Adventure** - Submit your hackathon idea
    - **Quest 2: Gathering the Party** - Define your team roles
    - **Quest 3: The Road of Trials** - Submit your GitHub repository
    - **Quest 4: The Return** - Submit your presentation link
    """)
    
    st.divider()
    
    # XP and leveling system
    st.subheader("✨ XP & Leveling System")
    st.markdown("""
    **Experience Points (XP):**
    - Earn **100 XP** for each quest completed
    - Total possible: **400 XP** (all 4 quests)
    
    **Leveling:**
    - Your level is calculated as: **Level = XP ÷ 100**
    - Complete all quests to reach **Level 4**!
    
    **Track Your Progress:**
    - View your XP, level, and all artifacts in the **Profile** tab
    - See which quests are unlocked in the quest tabs
    """)
    
    st.divider()
    
    st.success("🎯 Ready to begin? Head to Quest 1 to start your adventure!")


def render_sidebar_auth() -> None:
    """Render authentication form in sidebar.
    
    Displays:
    - Team name input field
    - PIN input field (password type)
    - Login/Create button
    
    Stores input in session state for processing by main app.
    
    Returns:
        None (renders UI directly via Streamlit)
        
    Validates:
        - Requirements 13.1 (sidebar authentication interface)
    """
    st.sidebar.header("🎮 Team Login")
    
    st.sidebar.markdown("""
    Enter your team name and PIN to login or create a new team.
    """)
    
    with st.sidebar.form(key="auth_form"):
        team_name = st.text_input(
            "Team Name:",
            max_chars=50,
            key="auth_team_name_input"
        )
        
        pin = st.text_input(
            "PIN:",
            type="password",
            max_chars=20,
            key="auth_pin_input"
        )
        
        submit_button = st.form_submit_button("Login / Create Team")
        
        if submit_button:
            # Store credentials in session state for processing
            st.session_state["auth_submission"] = {
                "team_name": team_name,
                "pin": pin
            }
