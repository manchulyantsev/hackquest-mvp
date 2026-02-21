"""
Unit tests for database module.
"""

import pytest
from datetime import datetime
from hackquest.database import (
    get_team, 
    create_team, 
    update_team_quest, 
    retry_with_backoff,
    RateLimitError,
    PersistenceError
)


class MockSheetsClient:
    """Mock Google Sheets client for testing."""
    
    def __init__(self):
        self.rows = []
        self.fail_count = 0
        self.fail_with_rate_limit = False
        self.fail_with_error = False
        
    def get_all_records(self):
        """Mock get_all_records method."""
        if self.fail_with_rate_limit and self.fail_count > 0:
            self.fail_count -= 1
            raise Exception("Rate limit exceeded (429)")
        if self.fail_with_error:
            raise Exception("Connection error")
        
        # Convert rows to dict records
        if not self.rows:
            return []
        
        records = []
        for row in self.rows:
            records.append({
                'Team_Name': row[0],
                'PIN_Hash': row[1],
                'Stage': row[2],
                'XP': row[3],
                'Idea_Text': row[4],
                'Roles_Text': row[5],
                'GitHub_Link': row[6],
                'Pitch_Link': row[7],
                'Timestamp': row[8]
            })
        return records
    
    def append_row(self, row):
        """Mock append_row method."""
        if self.fail_with_rate_limit and self.fail_count > 0:
            self.fail_count -= 1
            raise Exception("Rate limit exceeded (429)")
        if self.fail_with_error:
            raise Exception("Connection error")
        
        self.rows.append(row)
    
    def update_cell(self, row_num, col_num, value):
        """Mock update_cell method."""
        if self.fail_with_rate_limit and self.fail_count > 0:
            self.fail_count -= 1
            raise Exception("Rate limit exceeded (429)")
        if self.fail_with_error:
            raise Exception("Connection error")
        
        # Update the cell in the mock data
        if row_num - 2 < len(self.rows):  # -2 for header and 1-indexing
            self.rows[row_num - 2][col_num - 1] = value


class TestRetryWithBackoff:
    """Test retry with exponential backoff functionality."""
    
    def test_retry_success_first_attempt(self):
        """Function succeeds on first attempt."""
        call_count = [0]
        
        def success_func():
            call_count[0] += 1
            return "success"
        
        result = retry_with_backoff(success_func)
        assert result == "success"
        assert call_count[0] == 1
    
    def test_retry_success_after_rate_limit(self):
        """Function succeeds after rate limit error."""
        call_count = [0]
        
        def rate_limit_then_success():
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Rate limit exceeded (429)")
            return "success"
        
        result = retry_with_backoff(rate_limit_then_success)
        assert result == "success"
        assert call_count[0] == 2
    
    def test_retry_exhausted_rate_limit(self):
        """All retries exhausted with rate limit errors."""
        def always_rate_limit():
            raise Exception("Rate limit exceeded (429)")
        
        with pytest.raises(RateLimitError):
            retry_with_backoff(always_rate_limit, max_attempts=3)
    
    def test_retry_non_rate_limit_error(self):
        """Non-rate-limit errors raise immediately."""
        def connection_error():
            raise Exception("Connection failed")
        
        with pytest.raises(PersistenceError):
            retry_with_backoff(connection_error)


class TestGetTeam:
    """Test get_team functionality."""
    
    def test_get_team_exists(self):
        """Get team that exists in database."""
        mock_client = MockSheetsClient()
        mock_client.rows = [
            ['team1', 'hash123', 1, 0, '', '', '', '', '2024-01-01T00:00:00Z']
        ]
        
        team_data = get_team('team1', mock_client)
        
        assert team_data is not None
        assert team_data['team_name'] == 'team1'
        assert team_data['pin_hash'] == 'hash123'
        assert team_data['stage'] == 1
        assert team_data['xp'] == 0
        assert team_data['idea_text'] is None
        assert team_data['timestamp'] == '2024-01-01T00:00:00Z'
    
    def test_get_team_not_found(self):
        """Get team that doesn't exist returns None."""
        mock_client = MockSheetsClient()
        mock_client.rows = [
            ['team1', 'hash123', 1, 0, '', '', '', '', '2024-01-01T00:00:00Z']
        ]
        
        team_data = get_team('nonexistent', mock_client)
        
        assert team_data is None
    
    def test_get_team_with_artifacts(self):
        """Get team with submitted artifacts."""
        mock_client = MockSheetsClient()
        mock_client.rows = [
            ['team1', 'hash123', 3, 200, 'My idea', 'Our roles', 'github.com/repo', '', '2024-01-01T00:00:00Z']
        ]
        
        team_data = get_team('team1', mock_client)
        
        assert team_data is not None
        assert team_data['idea_text'] == 'My idea'
        assert team_data['roles_text'] == 'Our roles'
        assert team_data['github_link'] == 'github.com/repo'
        assert team_data['pitch_link'] is None
        assert team_data['stage'] == 3
        assert team_data['xp'] == 200
    
    def test_get_team_empty_database(self):
        """Get team from empty database returns None."""
        mock_client = MockSheetsClient()
        
        team_data = get_team('team1', mock_client)
        
        assert team_data is None
    
    def test_get_team_filters_by_team_name(self):
        """Get team only returns data for specified team (data isolation)."""
        mock_client = MockSheetsClient()
        # Add multiple teams to database
        mock_client.rows = [
            ['team_alpha', 'hash_alpha', 1, 0, 'Alpha idea', '', '', '', '2024-01-01T00:00:00Z'],
            ['team_beta', 'hash_beta', 2, 100, 'Beta idea', 'Beta roles', '', '', '2024-01-02T00:00:00Z'],
            ['team_gamma', 'hash_gamma', 3, 200, 'Gamma idea', 'Gamma roles', 'github.com/gamma', '', '2024-01-03T00:00:00Z']
        ]
        
        # Get team_beta - should only return team_beta's data
        team_data = get_team('team_beta', mock_client)
        
        assert team_data is not None
        assert team_data['team_name'] == 'team_beta'
        assert team_data['pin_hash'] == 'hash_beta'
        assert team_data['stage'] == 2
        assert team_data['xp'] == 100
        assert team_data['idea_text'] == 'Beta idea'
        assert team_data['roles_text'] == 'Beta roles'
        # Verify no data from other teams leaked
        assert 'Alpha' not in str(team_data.values())
        assert 'Gamma' not in str(team_data.values())


class TestCreateTeam:
    """Test create_team functionality."""
    
    def test_create_team_initial_values(self):
        """Create team with correct initial values."""
        mock_client = MockSheetsClient()
        
        team_data = create_team('new_team', 'hashed_pin', mock_client)
        
        assert team_data is not None
        assert team_data['team_name'] == 'new_team'
        assert team_data['pin_hash'] == 'hashed_pin'
        assert team_data['stage'] == 1
        assert team_data['xp'] == 0
        assert team_data['idea_text'] is None
        assert team_data['roles_text'] is None
        assert team_data['github_link'] is None
        assert team_data['pitch_link'] is None
        assert 'timestamp' in team_data
        
        # Verify row was added to sheet
        assert len(mock_client.rows) == 1
        assert mock_client.rows[0][0] == 'new_team'
        assert mock_client.rows[0][1] == 'hashed_pin'
        assert mock_client.rows[0][2] == 1
        assert mock_client.rows[0][3] == 0
    
    def test_create_team_timestamp_format(self):
        """Create team generates valid ISO8601 timestamp."""
        mock_client = MockSheetsClient()
        
        team_data = create_team('new_team', 'hashed_pin', mock_client)
        
        # Verify timestamp is ISO8601 format
        timestamp = team_data['timestamp']
        assert timestamp.endswith('Z')
        # Should be parseable as datetime
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))


class TestUpdateTeamQuest:
    """Test update_team_quest functionality."""
    
    def test_update_team_quest_idea(self):
        """Update team with Quest 1 (idea) completion."""
        mock_client = MockSheetsClient()
        mock_client.rows = [
            ['team1', 'hash123', 1, 0, '', '', '', '', '2024-01-01T00:00:00Z']
        ]
        
        quest_data = {
            'stage': 2,
            'xp': 100,
            'artifact_field': 'idea_text',
            'artifact_value': 'My great idea',
            'timestamp': '2024-01-02T00:00:00Z'
        }
        
        result = update_team_quest('team1', quest_data, mock_client)
        
        assert result is True
        # Verify updates
        assert mock_client.rows[0][2] == 2  # Stage
        assert mock_client.rows[0][3] == 100  # XP
        assert mock_client.rows[0][4] == 'My great idea'  # Idea_Text
        assert mock_client.rows[0][8] == '2024-01-02T00:00:00Z'  # Timestamp
    
    def test_update_team_quest_roles(self):
        """Update team with Quest 2 (roles) completion."""
        mock_client = MockSheetsClient()
        mock_client.rows = [
            ['team1', 'hash123', 2, 100, 'My idea', '', '', '', '2024-01-01T00:00:00Z']
        ]
        
        quest_data = {
            'stage': 3,
            'xp': 200,
            'artifact_field': 'roles_text',
            'artifact_value': 'Developer, Designer',
            'timestamp': '2024-01-03T00:00:00Z'
        }
        
        result = update_team_quest('team1', quest_data, mock_client)
        
        assert result is True
        assert mock_client.rows[0][2] == 3  # Stage
        assert mock_client.rows[0][3] == 200  # XP
        assert mock_client.rows[0][5] == 'Developer, Designer'  # Roles_Text
    
    def test_update_team_quest_github(self):
        """Update team with Quest 3 (GitHub) completion."""
        mock_client = MockSheetsClient()
        mock_client.rows = [
            ['team1', 'hash123', 3, 200, 'My idea', 'Roles', '', '', '2024-01-01T00:00:00Z']
        ]
        
        quest_data = {
            'stage': 4,
            'xp': 300,
            'artifact_field': 'github_link',
            'artifact_value': 'https://github.com/team/repo',
            'timestamp': '2024-01-04T00:00:00Z'
        }
        
        result = update_team_quest('team1', quest_data, mock_client)
        
        assert result is True
        assert mock_client.rows[0][2] == 4  # Stage
        assert mock_client.rows[0][3] == 300  # XP
        assert mock_client.rows[0][6] == 'https://github.com/team/repo'  # GitHub_Link
    
    def test_update_team_quest_pitch(self):
        """Update team with Quest 4 (pitch) completion."""
        mock_client = MockSheetsClient()
        mock_client.rows = [
            ['team1', 'hash123', 4, 300, 'My idea', 'Roles', 'github.com', '', '2024-01-01T00:00:00Z']
        ]
        
        quest_data = {
            'stage': 4,  # Stage stays at 4 for final quest
            'xp': 400,
            'artifact_field': 'pitch_link',
            'artifact_value': 'https://slides.com/pitch',
            'timestamp': '2024-01-05T00:00:00Z'
        }
        
        result = update_team_quest('team1', quest_data, mock_client)
        
        assert result is True
        assert mock_client.rows[0][3] == 400  # XP
        assert mock_client.rows[0][7] == 'https://slides.com/pitch'  # Pitch_Link
    
    def test_update_team_quest_team_not_found(self):
        """Update quest for nonexistent team returns False."""
        mock_client = MockSheetsClient()
        mock_client.rows = [
            ['team1', 'hash123', 1, 0, '', '', '', '', '2024-01-01T00:00:00Z']
        ]
        
        quest_data = {
            'stage': 2,
            'xp': 100,
            'artifact_field': 'idea_text',
            'artifact_value': 'My idea',
            'timestamp': '2024-01-02T00:00:00Z'
        }
        
        result = update_team_quest('nonexistent', quest_data, mock_client)
        
        assert result is False
    
    def test_update_team_quest_with_rate_limit_retry(self):
        """Update quest succeeds after rate limit retry."""
        mock_client = MockSheetsClient()
        mock_client.rows = [
            ['team1', 'hash123', 1, 0, '', '', '', '', '2024-01-01T00:00:00Z']
        ]
        mock_client.fail_with_rate_limit = True
        mock_client.fail_count = 1  # Fail once, then succeed
        
        quest_data = {
            'stage': 2,
            'xp': 100,
            'artifact_field': 'idea_text',
            'artifact_value': 'My idea',
            'timestamp': '2024-01-02T00:00:00Z'
        }
        
        result = update_team_quest('team1', quest_data, mock_client)
        
        assert result is True
    
    def test_update_team_quest_rate_limit_exhausted(self):
        """Update quest returns False when rate limit exhausted."""
        mock_client = MockSheetsClient()
        mock_client.rows = [
            ['team1', 'hash123', 1, 0, '', '', '', '', '2024-01-01T00:00:00Z']
        ]
        mock_client.fail_with_rate_limit = True
        mock_client.fail_count = 10  # Fail more than max attempts
        
        quest_data = {
            'stage': 2,
            'xp': 100,
            'artifact_field': 'idea_text',
            'artifact_value': 'My idea',
            'timestamp': '2024-01-02T00:00:00Z'
        }
        
        result = update_team_quest('team1', quest_data, mock_client)
        
        assert result is False
    
    def test_update_team_quest_filters_by_team_name(self):
        """Update quest only modifies specified team's data (data isolation)."""
        mock_client = MockSheetsClient()
        # Add multiple teams to database
        mock_client.rows = [
            ['team_alpha', 'hash_alpha', 1, 0, '', '', '', '', '2024-01-01T00:00:00Z'],
            ['team_beta', 'hash_beta', 1, 0, '', '', '', '', '2024-01-02T00:00:00Z'],
            ['team_gamma', 'hash_gamma', 1, 0, '', '', '', '', '2024-01-03T00:00:00Z']
        ]
        
        # Update only team_beta
        quest_data = {
            'stage': 2,
            'xp': 100,
            'artifact_field': 'idea_text',
            'artifact_value': 'Beta team idea',
            'timestamp': '2024-01-04T00:00:00Z'
        }
        
        result = update_team_quest('team_beta', quest_data, mock_client)
        
        assert result is True
        
        # Verify only team_beta was updated
        assert mock_client.rows[0][2] == 1  # team_alpha stage unchanged
        assert mock_client.rows[0][3] == 0  # team_alpha xp unchanged
        assert mock_client.rows[0][4] == ''  # team_alpha idea unchanged
        
        assert mock_client.rows[1][2] == 2  # team_beta stage updated
        assert mock_client.rows[1][3] == 100  # team_beta xp updated
        assert mock_client.rows[1][4] == 'Beta team idea'  # team_beta idea updated
        
        assert mock_client.rows[2][2] == 1  # team_gamma stage unchanged
        assert mock_client.rows[2][3] == 0  # team_gamma xp unchanged
        assert mock_client.rows[2][4] == ''  # team_gamma idea unchanged



class TestUpdateTeamPin:
    """Test update_team_pin functionality."""
    
    def test_update_team_pin_success(self):
        """Update team PIN successfully."""
        mock_client = MockSheetsClient()
        mock_client.rows = [
            ['team1', 'old_hash', 1, 0, '', '', '', '', '2024-01-01T00:00:00Z']
        ]
        
        from hackquest.database import update_team_pin
        result = update_team_pin('team1', 'new_hash_123', mock_client)
        
        assert result is True
        # Verify PIN_Hash was updated (column B, index 1)
        assert mock_client.rows[0][1] == 'new_hash_123'
        # Verify other fields unchanged
        assert mock_client.rows[0][0] == 'team1'
        assert mock_client.rows[0][2] == 1
        assert mock_client.rows[0][3] == 0
    
    def test_update_team_pin_team_not_found(self):
        """Update PIN for nonexistent team returns False."""
        mock_client = MockSheetsClient()
        mock_client.rows = [
            ['team1', 'hash123', 1, 0, '', '', '', '', '2024-01-01T00:00:00Z']
        ]
        
        from hackquest.database import update_team_pin
        result = update_team_pin('nonexistent', 'new_hash', mock_client)
        
        assert result is False
        # Verify original team's PIN unchanged
        assert mock_client.rows[0][1] == 'hash123'
    
    def test_update_team_pin_with_rate_limit_retry(self):
        """Update PIN succeeds after rate limit retry."""
        mock_client = MockSheetsClient()
        mock_client.rows = [
            ['team1', 'old_hash', 1, 0, '', '', '', '', '2024-01-01T00:00:00Z']
        ]
        mock_client.fail_with_rate_limit = True
        mock_client.fail_count = 1  # Fail once, then succeed
        
        from hackquest.database import update_team_pin
        result = update_team_pin('team1', 'new_hash', mock_client)
        
        assert result is True
        assert mock_client.rows[0][1] == 'new_hash'
    
    def test_update_team_pin_filters_by_team_name(self):
        """Update PIN only modifies specified team (data isolation)."""
        mock_client = MockSheetsClient()
        # Add multiple teams to database
        mock_client.rows = [
            ['team_alpha', 'hash_alpha', 1, 0, '', '', '', '', '2024-01-01T00:00:00Z'],
            ['team_beta', 'hash_beta', 2, 100, '', '', '', '', '2024-01-02T00:00:00Z'],
            ['team_gamma', 'hash_gamma', 3, 200, '', '', '', '', '2024-01-03T00:00:00Z']
        ]
        
        from hackquest.database import update_team_pin
        result = update_team_pin('team_beta', 'new_beta_hash', mock_client)
        
        assert result is True
        
        # Verify only team_beta's PIN was updated
        assert mock_client.rows[0][1] == 'hash_alpha'  # team_alpha unchanged
        assert mock_client.rows[1][1] == 'new_beta_hash'  # team_beta updated
        assert mock_client.rows[2][1] == 'hash_gamma'  # team_gamma unchanged
    
    def test_update_team_pin_empty_database(self):
        """Update PIN in empty database returns False."""
        mock_client = MockSheetsClient()
        
        from hackquest.database import update_team_pin
        result = update_team_pin('team1', 'new_hash', mock_client)
        
        assert result is False
