import unittest
from unittest.mock import patch, Mock
import json
import os
import sys
from datetime import datetime

# Add parent directory to path to import the Flask app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from user_request_queue_svc import app

class TestUserRequestQueueSvc(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        os.environ['QUEUE_DB_URI'] = 'postgresql://user:password@host:port/database'
        os.environ['BANK_ASSET_AGENT_URI'] = 'http://mock-bank-asset-agent'
        os.environ['BATCH_SIZE'] = '10'
        os.environ['REQUEST_TIMEOUT'] = '1'
        os.environ['POLLING_INTERVAL'] = '1'

    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {"status": "healthy"})

    @patch('user_request_queue_svc.requests.get')
    @patch('user_request_queue_svc.get_db_connection')
    def test_ready_endpoint(self, mock_db_connect, mock_requests_get):
        """Test readiness check endpoint."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock external service health checks
        mock_requests_get.return_value.status_code = 200
        mock_requests_get.return_value.raise_for_status = Mock()

        response = self.app.get('/ready')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {"status": "ready"})
        mock_cursor.execute.assert_called_with("SELECT 1")

    @patch('user_request_queue_svc.add_request_to_queue')
    def test_add_to_queue_success(self, mock_add_to_queue):
        """Test successful request addition to queue."""
        mock_add_to_queue.return_value = True
        
        request_data = {
            "uuid": "test-uuid-123",
            "tier1": 600.0,
            "tier2": 300.0,
            "tier3": 100.0,
            "purpose": "INVEST",
            "accountid": "1234567890"
        }
        
        response = self.app.post('/api/v1/queue',
                                 json=request_data)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'queued')
        self.assertEqual(data['uuid'], 'test-uuid-123')

    def test_add_to_queue_missing_uuid(self):
        """Test request addition with missing UUID."""
        request_data = {
            "tier1": 600.0,
            "tier2": 300.0,
            "tier3": 100.0,
            "purpose": "INVEST"
        }
        
        response = self.app.post('/api/v1/queue',
                                 json=request_data)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'failed')
        self.assertIn('Missing required fields', data['error'])

    def test_add_to_queue_invalid_purpose(self):
        """Test request addition with invalid purpose."""
        request_data = {
            "uuid": "test-uuid-123",
            "tier1": 600.0,
            "tier2": 300.0,
            "tier3": 100.0,
            "purpose": "INVALID"
        }
        
        response = self.app.post('/api/v1/queue',
                                 json=request_data)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'failed')
        self.assertIn('Invalid purpose', data['error'])

    @patch('user_request_queue_svc.get_db_connection')
    def test_get_queue_status_success(self, mock_db_connect):
        """Test successful queue status retrieval."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock database response
        mock_result = {
            'uuid': 'test-uuid-123',
            'accountid': '1234567890',
            'tier1': 600.0,
            'tier2': 300.0,
            'tier3': 100.0,
            'purpose': 'INVEST',
            'status': 'PROCESSING',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        mock_cursor.fetchone.return_value = mock_result
        
        response = self.app.get('/api/v1/queue/status/test-uuid-123')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['uuid'], 'test-uuid-123')
        self.assertEqual(data['status'], 'PROCESSING')

    @patch('user_request_queue_svc.get_db_connection')
    def test_get_queue_status_not_found(self, mock_db_connect):
        """Test queue status retrieval for non-existent request."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock no result found
        mock_cursor.fetchone.return_value = None
        
        response = self.app.get('/api/v1/queue/status/non-existent-uuid')
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'not_found')

    @patch('user_request_queue_svc.get_db_connection')
    def test_get_queue_stats_success(self, mock_db_connect):
        """Test successful queue statistics retrieval."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock database response
        mock_stats = {
            'total_requests': 100,
            'processing': 5,
            'completed': 90,
            'failed': 5
        }
        mock_cursor.fetchone.return_value = mock_stats
        
        response = self.app.get('/api/v1/queue/stats')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['total_requests'], 100)
        self.assertEqual(data['processing'], 5)
        self.assertEqual(data['completed'], 90)
        self.assertEqual(data['failed'], 5)

    def test_calculate_aggregate_tiers(self):
        """Test aggregate tier calculation logic."""
        from user_request_queue_svc import calculate_aggregate_tiers
        
        # Test data with mix of INVEST and WITHDRAW
        requests_data = [
            {'purpose': 'INVEST', 'tier1': 600.0, 'tier2': 300.0, 'tier3': 100.0},
            {'purpose': 'INVEST', 'tier1': 400.0, 'tier2': 200.0, 'tier3': 50.0},
            {'purpose': 'WITHDRAW', 'tier1': 200.0, 'tier2': 100.0, 'tier3': 25.0}
        ]
        
        T1, T2, T3 = calculate_aggregate_tiers(requests_data)
        
        # Expected: (600+400-200), (300+200-100), (100+50-25)
        self.assertEqual(T1, 800.0)
        self.assertEqual(T2, 400.0)
        self.assertEqual(T3, 125.0)

    @patch('user_request_queue_svc.requests.post')
    def test_call_bank_asset_agent_success(self, mock_post):
        """Test successful bank asset agent call."""
        from user_request_queue_svc import call_bank_asset_agent
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'SUCCESS'}
        mock_post.return_value = mock_response
        
        result = call_bank_asset_agent(1000.0, 500.0, 250.0)
        self.assertEqual(result, 'SUCCESS')

    @patch('user_request_queue_svc.requests.post')
    def test_call_bank_asset_agent_failure(self, mock_post):
        """Test bank asset agent call failure."""
        from user_request_queue_svc import call_bank_asset_agent
        
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        result = call_bank_asset_agent(1000.0, 500.0, 250.0)
        self.assertEqual(result, 'FAILED')

    def test_invalid_tier_values(self):
        """Test request with invalid tier values."""
        request_data = {
            "uuid": "test-uuid-123",
            "tier1": "invalid",
            "tier2": 300.0,
            "tier3": 100.0,
            "purpose": "INVEST"
        }
        
        response = self.app.post('/api/v1/queue',
                                 json=request_data)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'failed')

if __name__ == '__main__':
    print("🧪 Running User Request Queue Service Unit Tests")
    print("============================================================")
    unittest.main()
