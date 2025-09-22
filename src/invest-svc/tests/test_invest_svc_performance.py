import unittest
from unittest.mock import patch, Mock
import json
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent directory to path to import the Flask app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from invest_svc import app

class TestInvestSvcPerformance(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        os.environ['USER_PORTFOLIO_DB_URI'] = 'postgresql://user:password@host:port/database'
        os.environ['USER_TIER_AGENT_URI'] = 'http://mock-user-tier-agent'
        os.environ['BALANCE_READER_URI'] = 'http://mock-balance-reader'
        os.environ['REQUEST_TIMEOUT'] = '1'

    @patch('invest_svc.requests.get')
    @patch('invest_svc.requests.post')
    @patch('invest_svc.get_db_connection')
    def test_health_endpoint_performance(self, mock_db, mock_post, mock_get):
        """Test health endpoint performance."""
        start_time = time.time()
        
        # Make multiple health check requests
        for i in range(10):
            response = self.app.get('/health')
            self.assertEqual(response.status_code, 200)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Health endpoint: 10 requests completed in {duration:.3f} seconds")
        self.assertLess(duration, 1.0)  # Should complete in less than 1 second

    @patch('invest_svc.requests.get')
    @patch('invest_svc.requests.post')
    @patch('invest_svc.get_db_connection')
    def test_concurrent_investment_requests(self, mock_db, mock_post, mock_get):
        """Test handling multiple concurrent investment requests."""
        # Setup mocks
        mock_balance_response = Mock()
        mock_balance_response.status_code = 200
        mock_balance_response.json.return_value = {"balance": 50000.0}
        
        mock_tier_response = Mock()
        mock_tier_response.status_code = 200
        mock_tier_response.json.return_value = {
            "accountid": "1234567890",
            "amount": 1000.0,
            "uuid": "test-uuid",
            "tier1": 600.0,
            "tier2": 300.0,
            "tier3": 100.0
        }
        
        mock_get.return_value = mock_balance_response
        mock_post.return_value = mock_tier_response
        
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        
        def make_investment_request(request_id):
            """Make a single investment request."""
            response = self.app.post('/api/v1/invest',
                                     headers={'x-auth-account-id': f'123456789{request_id}', 
                                             'Authorization': 'Bearer test-token'},
                                     json={"amount": 1000.0})
            return {
                'request_id': request_id,
                'status_code': response.status_code,
                'response_time': time.time()
            }
        
        # Test concurrent requests
        start_time = time.time()
        results = []
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_investment_request, i) for i in range(5)]
            
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Verify all requests succeeded
        successful_requests = [r for r in results if r['status_code'] == 200]
        self.assertEqual(len(successful_requests), 5)
        
        print(f"Concurrent investment requests: 5 requests completed in {duration:.3f} seconds")
        self.assertLess(duration, 5.0)  # Should complete in reasonable time

    @patch('invest_svc.get_db_connection')
    def test_portfolio_retrieval_performance(self, mock_db_connect):
        """Test portfolio retrieval performance."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        from datetime import datetime
        portfolio_data = {
            'accountid': '1234567890',
            'currency': 'USD',
            'tier1_allocation': 60.0,
            'tier2_allocation': 30.0,
            'tier3_allocation': 10.0,
            'total_allocation': 100.0,
            'tier1_value': 6000.0,
            'tier2_value': 3000.0,
            'tier3_value': 1000.0,
            'total_value': 10000.0,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        mock_cursor.fetchone.return_value = portfolio_data
        
        start_time = time.time()
        
        # Make multiple portfolio retrieval requests
        for i in range(20):
            response = self.app.get('/api/v1/portfolio/1234567890')
            self.assertEqual(response.status_code, 200)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Portfolio retrieval: 20 requests completed in {duration:.3f} seconds")
        self.assertLess(duration, 2.0)  # Should complete quickly

    def test_error_handling_performance(self):
        """Test error handling performance."""
        start_time = time.time()
        
        # Make multiple requests that should fail quickly
        for i in range(10):
            response = self.app.post('/api/v1/invest',
                                     headers={'Authorization': 'Bearer test-token'},
                                     json={"amount": 1000.0})  # Missing account ID
            self.assertEqual(response.status_code, 401)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Error handling: 10 failed requests completed in {duration:.3f} seconds")
        self.assertLess(duration, 1.0)  # Should fail quickly

if __name__ == '__main__':
    print("🧪 Running Invest Service Performance Tests")
    print("============================================================")
    unittest.main()
