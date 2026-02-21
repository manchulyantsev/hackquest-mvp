"""Unit tests for analytics module."""

import json
from unittest.mock import Mock, patch

import pytest
import requests

from hackquest.analytics import send_stage_metric


class TestSendStageMetric:
    """Test suite for send_stage_metric function."""
    
    @patch('hackquest.analytics.requests.post')
    @patch('hackquest.analytics.time.time')
    def test_successful_metric_send(self, mock_time, mock_post):
        """Test successful metric submission to Datadog."""
        # Arrange
        mock_time.return_value = 1234567890
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # Act
        result = send_stage_metric("idea", "test-api-key")
        
        # Assert
        assert result is True
        mock_post.assert_called_once()
        
        # Verify payload structure
        call_args = mock_post.call_args
        payload = call_args.kwargs['json']
        
        assert payload['series'][0]['metric'] == 'hackquest.stage_completed'
        assert payload['series'][0]['type'] == 'count'
        assert payload['series'][0]['points'] == [[1234567890, 1]]
        assert payload['series'][0]['tags'] == ['stage:idea']
        
        # Verify headers
        headers = call_args.kwargs['headers']
        assert headers['DD-API-KEY'] == 'test-api-key'
        assert headers['Content-Type'] == 'application/json'
    
    @patch('hackquest.analytics.requests.post')
    def test_metric_send_with_different_stages(self, mock_post):
        """Test metric submission with different stage names."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        stages = ['idea', 'team', 'mvp', 'pitch']
        
        for stage in stages:
            result = send_stage_metric(stage, "test-api-key")
            assert result is True
            
            # Verify correct stage tag
            call_args = mock_post.call_args
            payload = call_args.kwargs['json']
            assert payload['series'][0]['tags'] == [f'stage:{stage}']
    
    @patch('hackquest.analytics.requests.post')
    def test_request_exception_returns_false(self, mock_post):
        """Test that request exceptions are caught and return False."""
        # Arrange
        mock_post.side_effect = requests.exceptions.RequestException("Network error")
        
        # Act
        result = send_stage_metric("idea", "test-api-key")
        
        # Assert
        assert result is False
    
    @patch('hackquest.analytics.requests.post')
    def test_http_error_returns_false(self, mock_post):
        """Test that HTTP errors are caught and return False."""
        # Arrange
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
        mock_post.return_value = mock_response
        
        # Act
        result = send_stage_metric("idea", "invalid-api-key")
        
        # Assert
        assert result is False
    
    @patch('hackquest.analytics.requests.post')
    def test_timeout_returns_false(self, mock_post):
        """Test that timeout errors are caught and return False."""
        # Arrange
        mock_post.side_effect = requests.exceptions.Timeout("Request timeout")
        
        # Act
        result = send_stage_metric("idea", "test-api-key")
        
        # Assert
        assert result is False
    
    @patch('hackquest.analytics.requests.post')
    def test_unexpected_exception_returns_false(self, mock_post):
        """Test that unexpected exceptions are caught and return False."""
        # Arrange
        mock_post.side_effect = Exception("Unexpected error")
        
        # Act
        result = send_stage_metric("idea", "test-api-key")
        
        # Assert
        assert result is False
    
    @patch('hackquest.analytics.requests.post')
    def test_timeout_parameter_set(self, mock_post):
        """Test that timeout parameter is set in request."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # Act
        send_stage_metric("idea", "test-api-key")
        
        # Assert
        call_args = mock_post.call_args
        assert call_args.kwargs['timeout'] == 5
