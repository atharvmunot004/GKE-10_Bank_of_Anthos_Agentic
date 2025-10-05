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
    
    @patch('app.core.database.ledger_db.get_transactions')
    def test_collect_user_transaction_history_success(self, mock_get_transactions, sample_transaction_data):
        """Test successful transaction history collection"""
        # Mock database response
        mock_transactions = [
            {
                "transaction_id": "tx-001",
                "from_acct": "test-account-123",
                "to_acct": "merchant-001",
                "from_route": "111111111",
                "to_route": "222222222",
                "amount": 50.0,
                "timestamp": "2024-01-01T10:00:00Z"
            },
            {
                "transaction_id": "tx-002",
                "from_acct": "employer-001",
                "to_acct": "test-account-123",
                "from_route": "333333333",
                "to_route": "111111111",
                "amount": 5000.0,
                "timestamp": "2024-01-01T09:00:00Z"
            }
        ]
        mock_get_transactions.return_value = mock_transactions
        
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
    
    @patch('app.core.database.ledger_db.get_transactions')
    def test_collect_user_transaction_history_http_error(self, mock_get_transactions):
        """Test transaction history collection with database error"""
        # Mock database error
        mock_get_transactions.side_effect = Exception("Database connection failed")
        
        result = collect_user_transaction_history.invoke({
            "accountid": "test-account-123",
            "limit": 100
        })
        
        result_data = json.loads(result)
        assert "error" in result_data
        assert "Database connection failed" in result_data["error"]
    
    @patch('app.core.database.ledger_db.get_transactions')
    def test_collect_user_transaction_history_exception(self, mock_get_transactions):
        """Test transaction history collection with general exception"""
        # Mock general exception
        mock_get_transactions.side_effect = Exception("Unexpected error")
        
        result = collect_user_transaction_history.invoke({
            "accountid": "test-account-123",
            "limit": 100
        })
        
        result_data = json.loads(result)
        assert "error" in result_data
        assert "Unexpected error" in result_data["error"]
    
    @patch('app.core.database.queue_db.publish_allocation')
    def test_publish_allocation_to_queue_success(self, mock_publish_allocation):
        """Test successful allocation publishing to queue"""
        # Mock database response
        mock_publish_allocation.return_value = {"success": True, "allocation_id": "queue-123", "uuid": "test-uuid-123"}
        
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
        assert "allocation_id" in result_data
    
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
    
    @patch('app.core.database.portfolio_db.add_transaction')
    def test_add_transaction_to_portfolio_db_success(self, mock_add_transaction):
        """Test successful transaction addition to portfolio DB"""
        # Mock database response
        mock_add_transaction.return_value = {"success": True, "transaction_id": "portfolio-123", "uuid": "test-uuid-123"}
        
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
        assert "transaction_id" in result_data
    
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
        with patch('app.core.database.ledger_db.get_transactions') as mock_get_transactions:
            mock_get_transactions.side_effect = Exception("Database timeout")
            
            result = collect_user_transaction_history.invoke({
            "accountid": "test-account-123",
            "limit": 100
        })
            result_data = json.loads(result)
            assert "error" in result_data
            assert "timeout" in result_data["error"].lower()
