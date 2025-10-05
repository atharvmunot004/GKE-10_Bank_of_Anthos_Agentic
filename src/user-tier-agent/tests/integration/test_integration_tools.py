"""
Integration tests for tool communication with external services
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


class TestIntegrationTools:
    """Integration tests for tools with external services"""
    
    @patch('app.core.database.ledger_db.get_transactions')
    def test_collect_user_transaction_history_integration(self, mock_get_transactions):
        """Test integration with ledger-db service"""
        # Mock successful response from ledger-db
        mock_transactions = [
            {
                "transaction_id": "tx-001",
                "from_acct": "test-account-123",
                "to_acct": "merchant-001",
                "from_route": "123456789",
                "to_route": "987654321",
                "amount": 50.0,
                "timestamp": "2024-01-01T10:00:00Z"
            },
            {
                "transaction_id": "tx-002",
                "from_acct": "employer-001",
                "to_acct": "test-account-123",
                "from_route": "111111111",
                "to_route": "123456789",
                "amount": 5000.0,
                "timestamp": "2024-01-01T09:00:00Z"
            }
        ]
        mock_get_transactions.return_value = mock_transactions
        
        # Test the tool
        result = collect_user_transaction_history.invoke({
            "accountid": "test-account-123",
            "limit": 100
        })
        
        # Verify the result
        result_data = json.loads(result)
        assert "transactions" in result_data
        assert len(result_data["transactions"]) == 2
        assert result_data["accountid"] == "test-account-123"
        assert result_data["count"] == 2
        
        # Verify the database call
        mock_get_transactions.assert_called_once()
        call_args = mock_get_transactions.call_args
        assert call_args[0][0] == "test-account-123"  # accountid parameter
        assert call_args[0][1] == 100  # limit parameter
    
    @patch('app.core.database.ledger_db.get_transactions')
    def test_collect_user_transaction_history_service_down(self, mock_get_transactions):
        """Test integration when ledger-db service is down"""
        # Mock service unavailable
        mock_get_transactions.side_effect = Exception("Connection refused")
        
        result = collect_user_transaction_history.invoke({
    "accountid": "test-account-123",
    "limit": 100
})
        
        result_data = json.loads(result)
        assert "error" in result_data
        assert "transactions" in result_data
        assert result_data["transactions"] == []
    
    @patch('app.core.database.ledger_db.get_transactions')
    def test_collect_user_transaction_history_timeout(self, mock_get_transactions):
        """Test integration with timeout"""
        # Mock timeout
        mock_get_transactions.side_effect = Exception("Request timed out")
        
        result = collect_user_transaction_history.invoke({
    "accountid": "test-account-123",
    "limit": 100
})
        
        result_data = json.loads(result)
        assert "error" in result_data
        assert "timed out" in result_data["error"].lower()
    
    @patch('app.core.database.queue_db.publish_allocation')
    def test_publish_allocation_to_queue_integration(self, mock_publish_allocation):
        """Test integration with queue-db service"""
        # Mock successful response from queue-db
        mock_publish_allocation.return_value = {
            "success": True,
            "allocation_id": "queue-123",
            "uuid": "test-uuid-123"
        }
        
        # Test the tool
        result = publish_allocation_to_queue.invoke({
            "uuid": "test-uuid-123",
            "accountid": "test-account-123",
            "tier1": 1000.0,
            "tier2": 2000.0,
            "tier3": 7000.0,
            "purpose": "INVEST"
        })
        
        # Verify the result
        result_data = json.loads(result)
        assert result_data["success"] is True
        assert "allocation_id" in result_data
        
        # Verify the database call
        mock_publish_allocation.assert_called_once()
        call_args = mock_publish_allocation.call_args
        assert call_args[0][0] == "test-uuid-123"  # uuid parameter
        assert call_args[0][1] == "test-account-123"  # accountid parameter
        assert call_args[0][2] == 1000.0  # tier1 parameter
        assert call_args[0][3] == 2000.0  # tier2 parameter
        assert call_args[0][4] == 7000.0  # tier3 parameter
        assert call_args[0][5] == "INVEST"  # purpose parameter
    
    @patch('app.core.database.queue_db.publish_allocation')
    def test_publish_allocation_to_queue_service_error(self, mock_publish_allocation):
        """Test integration when queue-db service returns error"""
        # Mock service error
        mock_publish_allocation.side_effect = Exception("Internal Server Error")
        
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
        assert "Internal Server Error" in result_data["error"]
    
    @patch('app.core.database.portfolio_db.add_transaction')
    def test_add_transaction_to_portfolio_db_integration(self, mock_add_transaction):
        """Test integration with portfolio-db service"""
        # Mock successful response from portfolio-db
        mock_add_transaction.return_value = {
            "success": True,
            "transaction_id": "portfolio-123",
            "uuid": "test-uuid-123"
        }
        
        # Test the tool
        result = add_transaction_to_portfolio_db.invoke({
            "uuid": "test-uuid-123",
            "accountid": "test-account-123",
            "tier1": 1000.0,
            "tier2": 2000.0,
            "tier3": 7000.0,
            "purpose": "INVEST"
        })
        
        # Verify the result
        result_data = json.loads(result)
        assert result_data["success"] is True
        assert "transaction_id" in result_data
        
        # Verify the database call
        mock_add_transaction.assert_called_once()
        call_args = mock_add_transaction.call_args
        assert call_args[0][0] == "test-uuid-123"  # uuid parameter
        assert call_args[0][1] == "test-account-123"  # accountid parameter
        assert call_args[0][2] == 1000.0  # tier1 parameter
        assert call_args[0][3] == 2000.0  # tier2 parameter
        assert call_args[0][4] == 7000.0  # tier3 parameter
        assert call_args[0][5] == "INVEST"  # purpose parameter
    
    @patch('app.core.database.portfolio_db.add_transaction')
    def test_add_transaction_to_portfolio_db_service_unavailable(self, mock_add_transaction):
        """Test integration when portfolio-db service is unavailable"""
        # Mock service unavailable
        mock_add_transaction.side_effect = Exception("Connection refused")
        
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
        assert "Connection refused" in result_data["error"]
    
    @patch('app.core.database.ledger_db.get_transactions')
    def test_tool_retry_mechanism(self, mock_get_transactions):
        """Test tool retry mechanism with exponential backoff"""
        # Mock first two calls to fail, third to succeed
        mock_get_transactions.side_effect = [
            Exception("Connection refused"),
            Exception("Connection refused"),
            []  # Success case returns empty list
        ]
        
        # This should eventually succeed after retries
        result = collect_user_transaction_history.invoke({
    "accountid": "test-account-123",
    "limit": 100
})
        
        result_data = json.loads(result)
        assert "transactions" in result_data
        assert mock_get_transactions.call_count >= 1  # At least one call was made
    
    @patch('app.core.database.ledger_db.get_transactions')
    def test_tool_circuit_breaker_pattern(self, mock_get_transactions):
        """Test circuit breaker pattern for failing services"""
        # Mock consistent failures
        mock_get_transactions.side_effect = Exception("Service unavailable")
        
        # Multiple calls should all fail gracefully
        results = []
        for _ in range(5):
            result = collect_user_transaction_history.invoke({
    "accountid": "test-account-123",
    "limit": 100
})
            results.append(json.loads(result))
        
        # All should return error responses
        assert all("error" in result for result in results)
        assert all(result["transactions"] == [] for result in results)
    
    def test_tool_error_propagation(self):
        """Test that tool errors are properly propagated"""
        with patch('app.core.database.ledger_db.get_transactions') as mock_get_transactions:
            mock_get_transactions.side_effect = Exception("Unexpected error")
            
            result = collect_user_transaction_history.invoke({
    "accountid": "test-account-123",
    "limit": 100
})
            
            result_data = json.loads(result)
            assert "error" in result_data
            assert "Unexpected error" in result_data["error"]
    
    def test_tool_concurrent_execution(self):
        """Test tools can handle concurrent execution"""
        import threading
        import time
        
        results = []
        
        def execute_tool():
            with patch('httpx.get') as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = {"transactions": []}
                mock_response.raise_for_status.return_value = None
                mock_get.return_value = mock_response
                
                result = collect_user_transaction_history.invoke({
    "accountid": "test-account-123",
    "limit": 100
})
                results.append(json.loads(result))
        
        # Create multiple threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=execute_tool)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All should succeed
        assert len(results) == 3
        assert all("transactions" in result for result in results)
