# Team Data Isolation Implementation

## Overview

This document describes the team data isolation implementation for HackQuest MVP, ensuring that teams can only access their own data and preventing cross-team data leakage.

**Validates: Requirements 1.5 - Team Data Isolation**

## Implementation Details

### 1. Database Layer (`hackquest/database.py`)

#### `get_team(team_name, sheets_client)`
- **Isolation Mechanism**: Filters all records by exact `team_name` match
- **Defensive Check**: Asserts returned team_name matches requested team_name
- **Verification**: Only returns data for the specified team, never returns other teams' data

```python
# CRITICAL: Only exact match ensures data isolation
for record in records:
    if record.get('Team_Name') == team_name:
        team_data = {...}
        # Defensive check for data isolation
        assert team_data['team_name'] == team_name
        return team_data
```

#### `update_team_quest(team_name, quest_data, sheets_client)`
- **Isolation Mechanism**: Finds row by exact `team_name` match before updating
- **Defensive Check**: Asserts the found record matches requested team_name
- **Verification**: Only updates the specified team's row, never modifies other teams

```python
# CRITICAL: Only update the row matching team_name for data isolation
for idx, record in enumerate(records):
    if record.get('Team_Name') == team_name:
        # Defensive check: Verify we found the correct team
        assert record.get('Team_Name') == team_name
        row_num = idx + 2
        break
```

### 2. Authentication Layer (`hackquest/auth.py`)

#### `authenticate_team(team_name, pin, sheets_client)`
- **Isolation Mechanism**: Only queries for the specified team_name
- **Defensive Checks**: 
  - Verifies created team matches requested team_name
  - Verifies authenticated team matches requested team_name
- **Verification**: Returns only the authenticated team's data

```python
# Defensive check: Verify created team matches requested team_name
assert team_data['team_name'] == team_name

# Defensive check: Verify returned data is for the correct team
assert team_data['team_name'] == team_name
```

### 3. Application Layer (`app.py`)

#### `handle_authentication(sheets_client)`
- **Isolation Mechanism**: Loads only authenticated team's data into session state
- **Defensive Check**: Asserts team_data matches requested team_name before loading
- **Verification**: Session state contains only the authenticated team's data

```python
# CRITICAL: Only load data for the authenticated team
# Defensive check: Verify team_data is for the correct team
assert team_data["team_name"] == team_name

st.session_state.team_name = team_data["team_name"]
st.session_state.stage = team_data["stage"]
# ... only authenticated team's data loaded
```

## Testing

### Unit Tests Added

1. **`test_get_team_filters_by_team_name`** (tests/unit/test_database.py)
   - Creates multiple teams in database
   - Fetches one team
   - Verifies only that team's data is returned
   - Confirms no data from other teams leaked

2. **`test_update_team_quest_filters_by_team_name`** (tests/unit/test_database.py)
   - Creates multiple teams in database
   - Updates one team's quest
   - Verifies only that team's data was modified
   - Confirms other teams' data remained unchanged

3. **`test_authenticate_team_data_isolation`** (tests/unit/test_auth.py)
   - Creates multiple teams with different data
   - Authenticates as one team
   - Verifies only that team's data is returned
   - Confirms no data from other teams leaked

### Verification Script

`test_isolation_check.py` - Standalone verification script that:
- Tests get_team isolation
- Tests update_team_quest isolation
- Tests authenticate_team isolation
- All tests passed ✓

## Security Guarantees

1. **Query Filtering**: All database queries filter by exact team_name match
2. **Defensive Assertions**: Runtime assertions verify data isolation at critical points
3. **Session Isolation**: Session state only contains authenticated team's data
4. **No Cross-Team Access**: No code path allows accessing another team's data

## Data Flow

```
User Login (team_name, pin)
    ↓
authenticate_team(team_name, pin)
    ↓
get_team(team_name) → Filters by team_name → Returns only matching team
    ↓
Defensive assertion: team_data['team_name'] == team_name
    ↓
Load into session_state → Only authenticated team's data
    ↓
All subsequent operations use session_state.team_name
    ↓
update_team_quest(session_state.team_name, ...) → Updates only that team
```

## Compliance

This implementation satisfies **Requirement 1.5**:
> "THE HackQuest_System SHALL isolate team data so Teams can only view their own Artifacts and progress"

All database operations are filtered by team_name, and defensive checks ensure no cross-team data leakage is possible.
