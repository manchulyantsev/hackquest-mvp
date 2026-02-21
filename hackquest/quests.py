"""Quest validation and progression logic for HackQuest MVP.

This module provides core quest mechanics including artifact validation,
level calculation, quest unlock status, and quest configuration.
"""

from typing import Tuple


def validate_artifact(artifact: str, max_length: int = 1000) -> Tuple[bool, str]:
    """Validate artifact input against length constraints.
    
    Args:
        artifact: The artifact string to validate
        max_length: Maximum allowed length (default: 1000)
    
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if validation passes, False otherwise
        - error_message: Empty string if valid, error description if invalid
    
    Validates:
        - Requirements 3.1, 4.1, 5.1, 6.1 (length validation)
        - Requirements 3.6, 4.6, 5.6, 6.6 (rejection on length violation)
    """
    if not artifact or len(artifact) < 1:
        return False, "Artifact cannot be empty"
    
    if len(artifact) > max_length:
        return False, f"Artifact must be between 1 and {max_length} characters (current: {len(artifact)})"
    
    return True, ""


def calculate_level(xp: int) -> int:
    """Calculate level from XP using integer division.
    
    Args:
        xp: Total experience points
    
    Returns:
        Level calculated as XP // 100
    
    Validates:
        - Requirements 7.3 (level calculation formula)
    """
    return xp // 100


def is_quest_unlocked(current_stage: int, quest_number: int) -> bool:
    """Check if a quest is unlocked based on current stage.
    
    Args:
        current_stage: The team's current stage (1-4)
        quest_number: The quest number to check (1-4)
    
    Returns:
        True if quest is unlocked, False if locked
    
    Validates:
        - Requirements 2.1, 2.2, 2.3, 2.4 (sequential unlocking)
        - Requirements 2.5 (quest lock enforcement)
    """
    return quest_number <= current_stage


# Quest configuration list with metadata for all quests
# Validates: Requirements 2.1-2.5, 3.1-3.6, 4.1-4.6, 5.1-5.6, 6.1-6.6
QUESTS = [
    {
        "number": 1,
        "title": "The Call to Adventure",
        "description": "Submit your hackathon idea",
        "artifact_field": "idea_text",
        "stage_tag": "idea",
        "xp_reward": 100
    },
    {
        "number": 2,
        "title": "Gathering the Party",
        "description": "Define your team roles",
        "artifact_field": "roles_text",
        "stage_tag": "team",
        "xp_reward": 100
    },
    {
        "number": 3,
        "title": "The Road of Trials",
        "description": "Submit your GitHub repository",
        "artifact_field": "github_link",
        "stage_tag": "mvp",
        "xp_reward": 100
    },
    {
        "number": 4,
        "title": "The Return",
        "description": "Submit your presentation link",
        "artifact_field": "pitch_link",
        "stage_tag": "pitch",
        "xp_reward": 100
    }
]
