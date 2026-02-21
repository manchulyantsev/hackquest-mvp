"""
Authentication module for HackQuest MVP.

Handles PIN-based team authentication with bcrypt hashing.
"""

import bcrypt


def hash_pin(pin: str) -> str:
    """
    Hash a PIN using bcrypt with automatic salt generation.
    
    Args:
        pin: The plaintext PIN to hash
        
    Returns:
        The bcrypt hash as a string
        
    Example:
        >>> pin_hash = hash_pin("1234")
        >>> pin_hash != "1234"  # Hash never equals plaintext
        True
    """
    # Convert PIN to bytes and generate hash with automatic salt
    pin_bytes = pin.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pin_bytes, salt)
    
    # Return as string for storage
    return hashed.decode('utf-8')


def verify_pin(pin: str, pin_hash: str) -> bool:
    """
    Verify a PIN against a stored bcrypt hash.
    
    Args:
        pin: The plaintext PIN to verify
        pin_hash: The stored bcrypt hash
        
    Returns:
        True if PIN matches hash, False otherwise
        
    Example:
        >>> pin_hash = hash_pin("1234")
        >>> verify_pin("1234", pin_hash)
        True
        >>> verify_pin("wrong", pin_hash)
        False
    """
    try:
        pin_bytes = pin.encode('utf-8')
        hash_bytes = pin_hash.encode('utf-8')
        return bcrypt.checkpw(pin_bytes, hash_bytes)
    except Exception:
        # Invalid hash format or other bcrypt errors
        return False


def authenticate_team(team_name: str, pin: str, sheets_client) -> dict | None:
    """
    Authenticate a team or create a new team if not found.
    
    TEAM DATA ISOLATION: This function only returns data for the authenticated team.
    Session state is populated exclusively with the authenticated team's data.
    
    This function implements create-or-login logic:
    1. Query Google Sheets for team_name
    2. If not found: hash PIN, create new team row with stage=1, xp=0
    3. If found: verify PIN against stored PIN_Hash
    4. On success: return team data dict
    5. On failure: return None
    
    Args:
        team_name: The team's unique identifier
        pin: The plaintext PIN
        sheets_client: Google Sheets client for database operations
        
    Returns:
        Team data dict on success, None on authentication failure
        
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
        
    Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5 (Team Data Isolation)
    """
    # Import here to avoid circular dependency
    from hackquest.database import get_team, create_team
    
    # Try to fetch existing team - only returns data for specified team_name
    team_data = get_team(team_name, sheets_client)
    
    if team_data is None:
        # Team doesn't exist - create new team
        pin_hash = hash_pin(pin)
        team_data = create_team(team_name, pin_hash, sheets_client)
        
        # Defensive check: Verify created team matches requested team_name
        assert team_data['team_name'] == team_name, \
            f"Data isolation violation: Created team {team_data['team_name']} != requested {team_name}"
        
        return team_data
    else:
        # Team exists - verify PIN
        stored_hash = team_data.get('pin_hash', '')
        if verify_pin(pin, stored_hash):
            # Defensive check: Verify returned data is for the correct team
            assert team_data['team_name'] == team_name, \
                f"Data isolation violation: Authenticated team {team_data['team_name']} != requested {team_name}"
            
            return team_data
        else:
            # Authentication failed
            return None
