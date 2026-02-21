"""
Database layer for HackQuest MVP.

Handles Google Sheets operations with retry logic for rate limits.
"""

import time
from datetime import datetime, UTC
from typing import Callable, Any


class RateLimitError(Exception):
    """Raised when Google Sheets API returns a rate limit error."""
    pass


class PersistenceError(Exception):
    """Raised when Google Sheets operations fail."""
    pass


def retry_with_backoff(func: Callable, max_attempts: int = 3) -> Any:
    """
    Retry a function with exponential backoff for rate limit errors.
    
    Implements exponential backoff: 1s, 2s, 4s between attempts.
    
    Args:
        func: The function to retry (should be a callable with no arguments)
        max_attempts: Maximum number of retry attempts (default: 3)
        
    Returns:
        The return value of the successful function call
        
    Raises:
        RateLimitError: If all retry attempts fail with rate limit errors
        PersistenceError: If the function fails with a non-rate-limit error
        
    Example:
        >>> result = retry_with_backoff(lambda: sheets.get_all_records())
    """
    for attempt in range(max_attempts):
        try:
            return func()
        except Exception as e:
            # Check if this is a rate limit error
            error_msg = str(e).lower()
            is_rate_limit = ('rate limit' in error_msg or 
                           'quota' in error_msg or 
                           '429' in error_msg)
            
            if is_rate_limit:
                if attempt == max_attempts - 1:
                    # Last attempt failed - raise RateLimitError
                    raise RateLimitError(f"Rate limit exceeded after {max_attempts} attempts") from e
                
                # Wait with exponential backoff: 1s, 2s, 4s
                wait_time = 2 ** attempt
                time.sleep(wait_time)
            else:
                # Non-rate-limit error - raise immediately
                raise PersistenceError(f"Database operation failed: {e}") from e
    
    # Should never reach here, but for type safety
    raise RateLimitError(f"Rate limit exceeded after {max_attempts} attempts")


def get_team(team_name: str, sheets_client) -> dict | None:
    """
    Fetch a team's data from Google Sheets.
    
    TEAM DATA ISOLATION: This function only returns data for the specified team_name.
    No cross-team data leakage is possible as filtering is done by exact team_name match.
    
    Args:
        team_name: The team's unique identifier
        sheets_client: Google Sheets client (gspread worksheet object)
        
    Returns:
        Team data dict if found, None if team doesn't exist
        
    Team data dict structure:
        {
            'team_name': str,
            'pin_hash': str,
            'stage': int,
            'xp': int,
            'idea_text': str | None,
            'roles_text': str | None,
            'github_link': str | None,
            'pitch_link': str | None,
            'timestamp': str
        }
        
    Raises:
        PersistenceError: If database operation fails
        RateLimitError: If rate limit is exceeded after retries
        
    Validates: Requirements 1.5 (Team Data Isolation)
    """
    def _get_team():
        # Get all records from the sheet
        records = sheets_client.get_all_records()
        
        # Find the team by name - CRITICAL: Only exact match ensures data isolation
        for record in records:
            if record.get('Team_Name') == team_name:
                # Convert sheet row to team data dict
                team_data = {
                    'team_name': record.get('Team_Name'),
                    'pin_hash': record.get('PIN_Hash', ''),
                    'stage': int(record.get('Stage', 1)),
                    'xp': int(record.get('XP', 0)),
                    'idea_text': record.get('Idea_Text') or None,
                    'roles_text': record.get('Roles_Text') or None,
                    'github_link': record.get('GitHub_Link') or None,
                    'pitch_link': record.get('Pitch_Link') or None,
                    'timestamp': record.get('Timestamp', '')
                }
                
                # Verify team_name matches (defensive check for data isolation)
                assert team_data['team_name'] == team_name, \
                    f"Data isolation violation: Expected {team_name}, got {team_data['team_name']}"
                
                return team_data
        
        # Team not found
        return None
    
    return retry_with_backoff(_get_team)


def create_team(team_name: str, pin_hash: str, sheets_client) -> dict:
    """
    Create a new team in Google Sheets with initial values.
    
    Initial values:
    - stage: 1 (Quest 1 unlocked)
    - xp: 0
    - All artifacts: None/empty
    - timestamp: current ISO8601 timestamp
    
    Args:
        team_name: The team's unique identifier
        pin_hash: The bcrypt hashed PIN
        sheets_client: Google Sheets client (gspread worksheet object)
        
    Returns:
        Team data dict for the newly created team
        
    Raises:
        PersistenceError: If database operation fails
        RateLimitError: If rate limit is exceeded after retries
    """
    def _create_team():
        # Generate timestamp
        timestamp = datetime.now(UTC).isoformat().replace('+00:00', 'Z')
        
        # Create new row with initial values
        new_row = [
            team_name,      # Team_Name
            pin_hash,       # PIN_Hash
            1,              # Stage (Quest 1 unlocked)
            0,              # XP
            '',             # Idea_Text (empty)
            '',             # Roles_Text (empty)
            '',             # GitHub_Link (empty)
            '',             # Pitch_Link (empty)
            timestamp       # Timestamp
        ]
        
        # Append row to sheet
        sheets_client.append_row(new_row)
        
        # Return team data dict
        return {
            'team_name': team_name,
            'pin_hash': pin_hash,
            'stage': 1,
            'xp': 0,
            'idea_text': None,
            'roles_text': None,
            'github_link': None,
            'pitch_link': None,
            'timestamp': timestamp
        }
    
    return retry_with_backoff(_create_team)


def update_team_quest(team_name: str, quest_data: dict, sheets_client) -> bool:
    """
    Update a team's quest completion data in Google Sheets.
    
    TEAM DATA ISOLATION: This function only updates data for the specified team_name.
    The function verifies the team exists and only modifies that team's row.
    
    This function updates:
    - Stage (incremented)
    - XP (increased by 100)
    - Artifact field (idea_text, roles_text, github_link, or pitch_link)
    - Timestamp (current time)
    
    Args:
        team_name: The team's unique identifier
        quest_data: Dict containing quest completion data
            {
                'stage': int,              # New stage number
                'xp': int,                 # New XP total
                'artifact_field': str,     # Field name (idea_text, roles_text, etc.)
                'artifact_value': str,     # Artifact content
                'timestamp': str           # ISO8601 timestamp
            }
        sheets_client: Google Sheets client (gspread worksheet object)
        
    Returns:
        True on success, False on failure
        
    Raises:
        PersistenceError: If database operation fails
        RateLimitError: If rate limit is exceeded after retries
        
    Validates: Requirements 1.5 (Team Data Isolation)
    """
    def _update_team():
        # Get all records to find the team's row
        records = sheets_client.get_all_records()
        
        # Find the team's row number (add 2 for header row and 1-indexing)
        # CRITICAL: Only update the row matching team_name for data isolation
        row_num = None
        for idx, record in enumerate(records):
            if record.get('Team_Name') == team_name:
                row_num = idx + 2  # +2 for header row and 1-indexing
                
                # Defensive check: Verify we found the correct team
                assert record.get('Team_Name') == team_name, \
                    f"Data isolation violation: Expected {team_name}, got {record.get('Team_Name')}"
                break
        
        if row_num is None:
            raise PersistenceError(f"Team '{team_name}' not found")
        
        # Map artifact field names to column indices (1-indexed)
        field_to_col = {
            'idea_text': 5,      # Column E
            'roles_text': 6,     # Column F
            'github_link': 7,    # Column G
            'pitch_link': 8      # Column H
        }
        
        # Update Stage (column C)
        sheets_client.update_cell(row_num, 3, quest_data['stage'])
        
        # Update XP (column D)
        sheets_client.update_cell(row_num, 4, quest_data['xp'])
        
        # Update artifact field
        artifact_field = quest_data['artifact_field']
        artifact_value = quest_data['artifact_value']
        if artifact_field in field_to_col:
            col_num = field_to_col[artifact_field]
            sheets_client.update_cell(row_num, col_num, artifact_value)
        
        # Update Timestamp (column I)
        sheets_client.update_cell(row_num, 9, quest_data['timestamp'])
        
        return True
    
    try:
        return retry_with_backoff(_update_team)
    except (PersistenceError, RateLimitError):
        return False


def update_team_pin(team_name: str, new_pin_hash: str, sheets_client) -> bool:
    """
    Update a team's PIN_Hash in Google Sheets for admin PIN recovery.
    
    This function allows admins to recover lost PINs by updating the PIN_Hash
    for a team. After updating, the team can authenticate with the new PIN.
    
    ADMIN USE ONLY: This function should only be called by hackathon organizers
    with direct access to the system, not exposed through the UI.
    
    Args:
        team_name: The team's unique identifier
        new_pin_hash: The new bcrypt hashed PIN
        sheets_client: Google Sheets client (gspread worksheet object)
        
    Returns:
        True if PIN was updated successfully, False if team not found
        
    Raises:
        PersistenceError: If database operation fails
        RateLimitError: If rate limit is exceeded after retries
        
    Example:
        >>> from hackquest.auth import hash_pin
        >>> new_pin = "new_secure_pin_1234"
        >>> new_pin_hash = hash_pin(new_pin)
        >>> success = update_team_pin("Team Alpha", new_pin_hash, sheets_client)
        >>> if success:
        ...     print("PIN updated successfully")
        
    Validates: Requirements 14.1, 14.2
    """
    def _update_pin():
        # Get all records to find the team's row
        records = sheets_client.get_all_records()
        
        # Find the team's row number (add 2 for header row and 1-indexing)
        row_num = None
        for idx, record in enumerate(records):
            if record.get('Team_Name') == team_name:
                row_num = idx + 2  # +2 for header row and 1-indexing
                
                # Defensive check: Verify we found the correct team
                assert record.get('Team_Name') == team_name, \
                    f"Team name mismatch: Expected {team_name}, got {record.get('Team_Name')}"
                break
        
        if row_num is None:
            # Team not found
            return False
        
        # Update PIN_Hash (column B, index 2)
        sheets_client.update_cell(row_num, 2, new_pin_hash)
        
        return True
    
    return retry_with_backoff(_update_pin)
