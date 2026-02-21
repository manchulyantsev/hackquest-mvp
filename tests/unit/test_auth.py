"""
Unit tests for authentication module.
"""

import pytest
from hackquest.auth import hash_pin, verify_pin, authenticate_team


class TestPinHashing:
    """Test PIN hashing functionality."""
    
    def test_hash_pin_returns_different_value(self):
        """Hash should never equal plaintext PIN."""
        pin = "1234"
        pin_hash = hash_pin(pin)
        assert pin_hash != pin
        
    def test_hash_pin_returns_string(self):
        """Hash should return a string."""
        pin = "test_pin"
        pin_hash = hash_pin(pin)
        assert isinstance(pin_hash, str)
        
    def test_hash_pin_different_salts(self):
        """Same PIN should produce different hashes due to different salts."""
        pin = "1234"
        hash1 = hash_pin(pin)
        hash2 = hash_pin(pin)
        assert hash1 != hash2  # Different salts


class TestPinVerification:
    """Test PIN verification functionality."""
    
    def test_verify_pin_correct_pin(self):
        """Correct PIN should verify successfully."""
        pin = "correct_pin"
        pin_hash = hash_pin(pin)
        assert verify_pin(pin, pin_hash) is True
        
    def test_verify_pin_incorrect_pin(self):
        """Incorrect PIN should fail verification."""
        pin = "correct_pin"
        pin_hash = hash_pin(pin)
        assert verify_pin("wrong_pin", pin_hash) is False
        
    def test_verify_pin_empty_pin(self):
        """Empty PIN should be handled correctly."""
        pin = ""
        pin_hash = hash_pin(pin)
        assert verify_pin("", pin_hash) is True
        assert verify_pin("nonempty", pin_hash) is False
        
    def test_verify_pin_invalid_hash(self):
        """Invalid hash format should return False."""
        assert verify_pin("any_pin", "invalid_hash") is False


class MockSheetsClient:
    """Mock Google Sheets client for testing."""
    
    def __init__(self):
        self.teams = {}
        
    def get_team(self, team_name):
        return self.teams.get(team_name)
        
    def create_team(self, team_name, pin_hash):
        team_data = {
            'team_name': team_name,
            'pin_hash': pin_hash,
            'stage': 1,
            'xp': 0,
            'idea_text': None,
            'roles_text': None,
            'github_link': None,
            'pitch_link': None,
            'timestamp': '2024-01-01T00:00:00Z'
        }
        self.teams[team_name] = team_data
        return team_data


class TestAuthenticateTeam:
    """Test team authentication functionality."""
    
    def test_authenticate_new_team(self, monkeypatch):
        """New team should be created and authenticated."""
        mock_client = MockSheetsClient()
        
        # Mock database functions
        monkeypatch.setattr('hackquest.database.get_team', 
                           lambda name, client: mock_client.get_team(name))
        monkeypatch.setattr('hackquest.database.create_team',
                           lambda name, pin_hash, client: mock_client.create_team(name, pin_hash))
        
        team_data = authenticate_team("new_team", "1234", mock_client)
        
        assert team_data is not None
        assert team_data['team_name'] == "new_team"
        assert team_data['stage'] == 1
        assert team_data['xp'] == 0
        assert team_data['pin_hash'] != "1234"  # Should be hashed
        
    def test_authenticate_existing_team_correct_pin(self, monkeypatch):
        """Existing team with correct PIN should authenticate."""
        mock_client = MockSheetsClient()
        
        # Create team first
        pin_hash = hash_pin("1234")
        mock_client.create_team("existing_team", pin_hash)
        
        # Mock database functions
        monkeypatch.setattr('hackquest.database.get_team',
                           lambda name, client: mock_client.get_team(name))
        monkeypatch.setattr('hackquest.database.create_team',
                           lambda name, pin_hash, client: mock_client.create_team(name, pin_hash))
        
        team_data = authenticate_team("existing_team", "1234", mock_client)
        
        assert team_data is not None
        assert team_data['team_name'] == "existing_team"
        
    def test_authenticate_existing_team_incorrect_pin(self, monkeypatch):
        """Existing team with incorrect PIN should fail authentication."""
        mock_client = MockSheetsClient()
        
        # Create team first
        pin_hash = hash_pin("1234")
        mock_client.create_team("existing_team", pin_hash)
        
        # Mock database functions
        monkeypatch.setattr('hackquest.database.get_team',
                           lambda name, client: mock_client.get_team(name))
        monkeypatch.setattr('hackquest.database.create_team',
                           lambda name, pin_hash, client: mock_client.create_team(name, pin_hash))
        
        team_data = authenticate_team("existing_team", "wrong_pin", mock_client)
        
        assert team_data is None
    
    def test_authenticate_team_data_isolation(self, monkeypatch):
        """Authenticating as one team should not return another team's data."""
        mock_client = MockSheetsClient()
        
        # Create multiple teams
        pin_hash_alpha = hash_pin("pin_alpha")
        pin_hash_beta = hash_pin("pin_beta")
        
        team_alpha = mock_client.create_team("team_alpha", pin_hash_alpha)
        team_alpha['idea_text'] = "Alpha's secret idea"
        team_alpha['xp'] = 100
        
        team_beta = mock_client.create_team("team_beta", pin_hash_beta)
        team_beta['idea_text'] = "Beta's secret idea"
        team_beta['xp'] = 200
        
        # Mock database functions
        monkeypatch.setattr('hackquest.database.get_team',
                           lambda name, client: mock_client.get_team(name))
        monkeypatch.setattr('hackquest.database.create_team',
                           lambda name, pin_hash, client: mock_client.create_team(name, pin_hash))
        
        # Authenticate as team_alpha
        team_data = authenticate_team("team_alpha", "pin_alpha", mock_client)
        
        assert team_data is not None
        assert team_data['team_name'] == "team_alpha"
        assert team_data['idea_text'] == "Alpha's secret idea"
        assert team_data['xp'] == 100
        # Verify no data from team_beta leaked
        assert "Beta" not in str(team_data.values())
        assert team_data['xp'] != 200
