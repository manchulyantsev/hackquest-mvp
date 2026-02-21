"""Unit tests for quest validation and progression logic."""

import pytest
from hackquest.quests import (
    validate_artifact,
    calculate_level,
    is_quest_unlocked,
    QUESTS
)


class TestValidateArtifact:
    """Test artifact validation logic."""
    
    def test_valid_artifact(self):
        """Test validation passes for valid artifact."""
        is_valid, error = validate_artifact("Valid hackathon idea")
        assert is_valid is True
        assert error == ""
    
    def test_empty_artifact(self):
        """Test validation fails for empty artifact."""
        is_valid, error = validate_artifact("")
        assert is_valid is False
        assert "empty" in error.lower()
    
    def test_artifact_at_max_length(self):
        """Test validation passes for artifact at exactly max length."""
        artifact = "x" * 1000
        is_valid, error = validate_artifact(artifact)
        assert is_valid is True
        assert error == ""
    
    def test_artifact_exceeds_max_length(self):
        """Test validation fails for artifact exceeding max length."""
        artifact = "x" * 1001
        is_valid, error = validate_artifact(artifact)
        assert is_valid is False
        assert "1000" in error
        assert "1001" in error
    
    def test_artifact_minimum_length(self):
        """Test validation passes for single character artifact."""
        is_valid, error = validate_artifact("x")
        assert is_valid is True
        assert error == ""
    
    def test_custom_max_length(self):
        """Test validation with custom max length."""
        artifact = "x" * 51
        is_valid, error = validate_artifact(artifact, max_length=50)
        assert is_valid is False
        assert "50" in error


class TestCalculateLevel:
    """Test level calculation logic."""
    
    def test_level_zero(self):
        """Test level 0 for XP less than 100."""
        assert calculate_level(0) == 0
        assert calculate_level(50) == 0
        assert calculate_level(99) == 0
    
    def test_level_one(self):
        """Test level 1 for XP 100-199."""
        assert calculate_level(100) == 1
        assert calculate_level(150) == 1
        assert calculate_level(199) == 1
    
    def test_level_four(self):
        """Test level 4 for completing all quests."""
        assert calculate_level(400) == 4
    
    def test_level_high_xp(self):
        """Test level calculation for high XP values."""
        assert calculate_level(1000) == 10
        assert calculate_level(9999) == 99


class TestIsQuestUnlocked:
    """Test quest unlock logic."""
    
    def test_quest_1_unlocked_initially(self):
        """Test Quest 1 is unlocked at stage 1."""
        assert is_quest_unlocked(1, 1) is True
    
    def test_quest_2_locked_initially(self):
        """Test Quest 2 is locked at stage 1."""
        assert is_quest_unlocked(1, 2) is False
    
    def test_quest_2_unlocked_at_stage_2(self):
        """Test Quest 2 is unlocked at stage 2."""
        assert is_quest_unlocked(2, 2) is True
    
    def test_quest_3_unlocked_at_stage_3(self):
        """Test Quest 3 is unlocked at stage 3."""
        assert is_quest_unlocked(3, 3) is True
    
    def test_quest_4_unlocked_at_stage_4(self):
        """Test Quest 4 is unlocked at stage 4."""
        assert is_quest_unlocked(4, 4) is True
    
    def test_all_quests_unlocked_at_stage_4(self):
        """Test all quests are unlocked at stage 4."""
        assert is_quest_unlocked(4, 1) is True
        assert is_quest_unlocked(4, 2) is True
        assert is_quest_unlocked(4, 3) is True
        assert is_quest_unlocked(4, 4) is True


class TestQuestsConfiguration:
    """Test QUESTS configuration list."""
    
    def test_quests_count(self):
        """Test there are exactly 4 quests."""
        assert len(QUESTS) == 4
    
    def test_quest_numbers(self):
        """Test quest numbers are sequential 1-4."""
        for i, quest in enumerate(QUESTS):
            assert quest["number"] == i + 1
    
    def test_quest_1_configuration(self):
        """Test Quest 1 configuration."""
        quest = QUESTS[0]
        assert quest["number"] == 1
        assert quest["title"] == "The Call to Adventure"
        assert quest["description"] == "Submit your hackathon idea"
        assert quest["artifact_field"] == "idea_text"
        assert quest["stage_tag"] == "idea"
        assert quest["xp_reward"] == 100
    
    def test_quest_2_configuration(self):
        """Test Quest 2 configuration."""
        quest = QUESTS[1]
        assert quest["number"] == 2
        assert quest["title"] == "Gathering the Party"
        assert quest["description"] == "Define your team roles"
        assert quest["artifact_field"] == "roles_text"
        assert quest["stage_tag"] == "team"
        assert quest["xp_reward"] == 100
    
    def test_quest_3_configuration(self):
        """Test Quest 3 configuration."""
        quest = QUESTS[2]
        assert quest["number"] == 3
        assert quest["title"] == "The Road of Trials"
        assert quest["description"] == "Submit your GitHub repository"
        assert quest["artifact_field"] == "github_link"
        assert quest["stage_tag"] == "mvp"
        assert quest["xp_reward"] == 100
    
    def test_quest_4_configuration(self):
        """Test Quest 4 configuration."""
        quest = QUESTS[3]
        assert quest["number"] == 4
        assert quest["title"] == "The Return"
        assert quest["description"] == "Submit your presentation link"
        assert quest["artifact_field"] == "pitch_link"
        assert quest["stage_tag"] == "pitch"
        assert quest["xp_reward"] == 100
    
    def test_all_quests_have_required_fields(self):
        """Test all quests have required configuration fields."""
        required_fields = ["number", "title", "description", "artifact_field", "stage_tag", "xp_reward"]
        for quest in QUESTS:
            for field in required_fields:
                assert field in quest, f"Quest {quest.get('number')} missing field: {field}"
    
    def test_all_quests_award_100_xp(self):
        """Test all quests award exactly 100 XP."""
        for quest in QUESTS:
            assert quest["xp_reward"] == 100
