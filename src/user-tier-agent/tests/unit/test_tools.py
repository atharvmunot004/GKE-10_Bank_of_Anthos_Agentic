"""
Unit tests for LangChain tools
"""

import pytest
import json
from unittest.mock import patch, Mock
import httpx

from app.services.tools import (
    collect_user_transaction_history,
    publish_allocation_to_queue,
    add_transaction_to_portfolio_db
)


class TestTools:
    """Test cases for LangChain tools"""
    
    @patch('httpx.get')
    def test_collect_user_transaction_history_success(self, mock_get, sample_transaction_data):
        """Test successful transaction history collection"""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.json.return_value = {"transactions": sample_transaction_data["transactions"]}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = collect_user_transaction_history.invoke({
            "accountid": "test-account-123",
            "limit": 100
        })
        
        assert isinstance(result, str)
        result_data = json.loads(result)
        assert "transactions" in result_data
        assert len(result_data["transactions"]) == 2
        assert result_data["accountid"] == "test-account-123"
        assert result_data["count"] == 2
    
    @patch('httpx.get')
    def test_collect_user_transaction_history_http_error(self, mock_get):
        """Test transaction history collection with HTTP error"""
        # Mock HTTP error
        mock_get.side_effect = httpx.HTTPError("Connection failed")
        
        result = collect_user_transaction_history.invoke({
            "accountid": "test-account-123",
            "limit": 100
        })
        
        result_data = json.loads(result)
        assert "error" in result_data
        assert "transactions" in result_data
        assert result_data["transactions"] == []
    
    @patch('httpx.get')
    def test_collect_user_transaction_history_exception(self, mock_get):
        """Test transaction history collection with general exception"""
        # Mock general exception
        mock_get.side_effect = Exception("Unexpected error")
        
        result = collect_user_transaction_history.invoke({
            "accountid": "test-account-123",
            "limit": 100
        })
        
        result_data = json.loads(result)
        assert "error" in result_data
        assert "transactions" in result_data
        assert result_data["transactions"] == []
    
    @patch('httpx.post')
    def test_publish_allocation_to_queue_success(self, mock_post):
        """Test successful allocation publishing to queue"""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.json.return_value = {"status": "success", "id": "queue-123"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = publish_allocation_to_queue.invoke({
            "uuid": "test-uuid-123",
            "accountid": "test-account-123",
            "tier1": 1000.0,
            "tier2": 2000.0,
            "tier3": 7000.0,
            "purpose": "INVEST"
        })
        
        assert isinstance(result, str)
        result_data = json.loads(result)
        assert result_data["success"] is True
        assert "result" in result_data
    
    @patch('httpx.post')
    def test_publish_allocation_to_queue_http_error(self, mock_post):
        """Test allocation publishing with HTTP error"""
        # Mock HTTP error
        mock_post.side_effect = httpx.HTTPError("Queue service unavailable")
        
        result = publish_allocation_to_queue.invoke({
            "uuid": "test-uuid-123",
            "accountid": "test-account-123",
            "tier1": 1000.0,
            "tier2": 2000.0,
            "tier3": 7000.0,
            "purpose": "INVEST"
        })
        
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "error" in result_data
    
    @patch('httpx.post')
    def test_publish_allocation_to_queue_exception(self, mock_post):
        """Test allocation publishing with general exception"""
        # Mock general exception
        mock_post.side_effect = Exception("Unexpected error")
        
        result = publish_allocation_to_queue.invoke({
            "uuid": "test-uuid-123",
            "accountid": "test-account-123",
            "tier1": 1000.0,
            "tier2": 2000.0,
            "tier3": 7000.0,
            "purpose": "INVEST"
        })
        
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "error" in result_data
    
    @patch('httpx.post')
    def test_add_transaction_to_portfolio_db_success(self, mock_post):
        """Test successful transaction addition to portfolio DB"""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.json.return_value = {"status": "success", "id": "portfolio-123"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = add_transaction_to_portfolio_db.invoke({
            "uuid": "test-uuid-123",
            "accountid": "test-account-123",
            "tier1": 1000.0,
            "tier2": 2000.0,
            "tier3": 7000.0,
            "purpose": "INVEST"
        })
        
        assert isinstance(result, str)
        result_data = json.loads(result)
        assert result_data["success"] is True
        assert "result" in result_data
    
    @patch('httpx.post')
    def test_add_transaction_to_portfolio_db_http_error(self, mock_post):
        """Test transaction addition with HTTP error"""
        # Mock HTTP error
        mock_post.side_effect = httpx.HTTPError("Portfolio service unavailable")
        
        result = add_transaction_to_portfolio_db.invoke({
            "uuid": "test-uuid-123",
            "accountid": "test-account-123",
            "tier1": 1000.0,
            "tier2": 2000.0,
            "tier3": 7000.0,
            "purpose": "INVEST"
        })
        
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "error" in result_data
    
    @patch('httpx.post')
    def test_add_transaction_to_portfolio_db_exception(self, mock_post):
        """Test transaction addition with general exception"""
        # Mock general exception
        mock_post.side_effect = Exception("Unexpected error")
        
        result = add_transaction_to_portfolio_db.invoke({
            "uuid": "test-uuid-123",
            "accountid": "test-account-123",
            "tier1": 1000.0,
            "tier2": 2000.0,
            "tier3": 7000.0,
            "purpose": "INVEST"
        })
        
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "error" in result_data
    
    def test_tool_parameter_validation(self):
        """Test tool parameter validation"""
        # Test with invalid parameters
        with patch('httpx.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"transactions": []}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            # Should handle invalid account ID gracefully
            result = collect_user_transaction_history.invoke({
            "accountid": "",
            "limit": 100
        })
            result_data = json.loads(result)
            assert "transactions" in result_data
    
    def test_tool_timeout_handling(self):
        """Test tool timeout handling"""
        with patch('httpx.get') as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timed out")
            
            result = collect_user_transaction_history.invoke({
            "accountid": "test-account-123",
            "limit": 100
        })
            result_data = json.loads(result)
            assert "error" in result_data
            assert "timed out" in result_data["error"].lower()
