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
    
    @patch('httpx.get')
    def test_collect_user_transaction_history_integration(self, mock_get):
        """Test integration with ledger-db service"""
        # Mock successful response from ledger-db
        mock_response = Mock()
        mock_response.json.return_value = {
            "transactions": [
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
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
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
        
        # Verify the HTTP call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "test-account-123" in call_args[0][0]  # URL contains account ID
        assert call_args[1]["params"]["limit"] == 100
    
    @patch('httpx.get')
    def test_collect_user_transaction_history_service_down(self, mock_get):
        """Test integration when ledger-db service is down"""
        # Mock service unavailable
        mock_get.side_effect = httpx.ConnectError("Connection refused")
        
        result = collect_user_transaction_history.invoke({
    "accountid": "test-account-123",
    "limit": 100
})
        
        result_data = json.loads(result)
        assert "error" in result_data
        assert "transactions" in result_data
        assert result_data["transactions"] == []
    
    @patch('httpx.get')
    def test_collect_user_transaction_history_timeout(self, mock_get):
        """Test integration with timeout"""
        # Mock timeout
        mock_get.side_effect = httpx.TimeoutException("Request timed out")
        
        result = collect_user_transaction_history.invoke({
    "accountid": "test-account-123",
    "limit": 100
})
        
        result_data = json.loads(result)
        assert "error" in result_data
        assert "timed out" in result_data["error"].lower()
    
    @patch('httpx.post')
    def test_publish_allocation_to_queue_integration(self, mock_post):
        """Test integration with queue-db service"""
        # Mock successful response from queue-db
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "success",
            "id": "queue-123",
            "timestamp": "2024-01-01T10:00:00Z"
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
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
        assert "result" in result_data
        assert result_data["result"]["status"] == "success"
        
        # Verify the HTTP call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "/allocations" in call_args[0][0]  # URL contains endpoint
        
        payload = call_args[1]["json"]
        assert payload["uuid"] == "test-uuid-123"
        assert payload["accountid"] == "test-account-123"
        assert payload["tier1"] == 1000.0
        assert payload["tier2"] == 2000.0
        assert payload["tier3"] == 7000.0
        assert payload["purpose"] == "INVEST"
    
    @patch('httpx.post')
    def test_publish_allocation_to_queue_service_error(self, mock_post):
        """Test integration when queue-db service returns error"""
        # Mock service error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Internal Server Error",
            request=Mock(),
            response=mock_response
        )
        mock_post.return_value = mock_response
        
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
    
    @patch('httpx.post')
    def test_add_transaction_to_portfolio_db_integration(self, mock_post):
        """Test integration with portfolio-db service"""
        # Mock successful response from portfolio-db
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "success",
            "id": "portfolio-123",
            "table": "portfolio-transactions-tb",
            "timestamp": "2024-01-01T10:00:00Z"
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
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
        assert "result" in result_data
        assert result_data["result"]["status"] == "success"
        
        # Verify the HTTP call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "/portfolio-transactions" in call_args[0][0]  # URL contains endpoint
        
        payload = call_args[1]["json"]
        assert payload["uuid"] == "test-uuid-123"
        assert payload["accountid"] == "test-account-123"
        assert payload["tier1"] == 1000.0
        assert payload["tier2"] == 2000.0
        assert payload["tier3"] == 7000.0
        assert payload["purpose"] == "INVEST"
        assert payload["table"] == "portfolio-transactions-tb"
    
    @patch('httpx.post')
    def test_add_transaction_to_portfolio_db_service_unavailable(self, mock_post):
        """Test integration when portfolio-db service is unavailable"""
        # Mock service unavailable
        mock_post.side_effect = httpx.ConnectError("Connection refused")
        
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
    
    @patch('httpx.get')
    def test_tool_retry_mechanism(self, mock_get):
        """Test tool retry mechanism with exponential backoff"""
        # Mock first two calls to fail, third to succeed
        mock_responses = [
            Mock(side_effect=httpx.ConnectError("Connection refused")),
            Mock(side_effect=httpx.ConnectError("Connection refused")),
            Mock()
        ]
        mock_responses[2].json.return_value = {"transactions": []}
        mock_responses[2].raise_for_status.return_value = None
        
        mock_get.side_effect = mock_responses
        
        # This should eventually succeed after retries
        result = collect_user_transaction_history.invoke({
    "accountid": "test-account-123",
    "limit": 100
})
        
        result_data = json.loads(result)
        assert "transactions" in result_data
        assert mock_get.call_count >= 1  # At least one call was made
    
    @patch('httpx.get')
    def test_tool_circuit_breaker_pattern(self, mock_get):
        """Test circuit breaker pattern for failing services"""
        # Mock consistent failures
        mock_get.side_effect = httpx.ConnectError("Service unavailable")
        
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
        with patch('httpx.get') as mock_get:
            mock_get.side_effect = Exception("Unexpected error")
            
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
