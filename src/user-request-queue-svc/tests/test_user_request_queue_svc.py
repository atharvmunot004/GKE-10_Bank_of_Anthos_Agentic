import unittest
from unittest.mock import patch, Mock, MagicMock
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
        os.environ['BANK_ASSET_AGENT_URI'] = 'http://bank-asset-agent:8080'
        os.environ['BATCH_SIZE'] = '10'
        os.environ['REQUEST_TIMEOUT'] = '1'
        os.environ['POLLING_INTERVAL'] = '5'
        os.environ['TIER1'] = '1000000.0'
        os.environ['TIER2'] = '2000000.0'
        os.environ['TIER3'] = '500000.0'

    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {"status": "healthy"})

    @patch('user_request_queue_svc.get_db_connection')
    @patch('user_request_queue_svc.requests.get')
    def test_ready_endpoint(self, mock_requests_get, mock_db_connect):
        """Test readiness check endpoint."""
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock bank-asset-agent health check
        mock_response = Mock()
        mock_response.status_code = 200
        mock_requests_get.return_value = mock_response
        
        response = self.app.get('/ready')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {"status": "ready"})
        mock_cursor.execute.assert_called_with("SELECT 1")

    def test_add_to_queue_missing_fields(self):
        """Test add to queue with missing required fields."""
        response = self.app.post('/api/v1/queue',
                                 json={"uuid": "test-uuid"})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'failed')
        self.assertIn('Missing required fields', data['error'])

    @patch('user_request_queue_svc.get_db_connection')
    def test_add_to_queue_success(self, mock_db_connect):
        """Test successful add to queue."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        queue_data = {
            "uuid": "test-uuid-001",
            "tier1": 1000.0,
            "tier2": 2000.0,
            "tier3": 500.0,
            "purpose": "INVEST",
            "accountid": "1234567890"
        }
        
        response = self.app.post('/api/v1/queue', json=queue_data)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'queued')
        self.assertEqual(data['uuid'], 'test-uuid-001')
        mock_cursor.execute.assert_called()

    @patch('user_request_queue_svc.get_db_connection')
    def test_get_queue_status_success(self, mock_db_connect):
        """Test successful queue status retrieval."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock database response
        mock_result = {
            'uuid': 'test-uuid-001',
            'accountid': '1234567890',
            'tier1': 1000.0,
            'tier2': 2000.0,
            'tier3': 500.0,
            'purpose': 'INVEST',
            'status': 'PROCESSING',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        mock_cursor.fetchone.return_value = mock_result
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        response = self.app.get('/api/v1/queue/status/test-uuid-001')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['uuid'], 'test-uuid-001')
        self.assertEqual(data['purpose'], 'INVEST')

    @patch('user_request_queue_svc.get_db_connection')
    def test_get_queue_status_not_found(self, mock_db_connect):
        """Test queue status retrieval when UUID not found."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = None
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        response = self.app.get('/api/v1/queue/status/nonexistent-uuid')
        
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
            'total_requests': 10,
            'processing': 5,
            'completed': 3,
            'failed': 2
        }
        mock_cursor.fetchone.return_value = mock_stats
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        response = self.app.get('/api/v1/queue/stats')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['total_requests'], 10)
        self.assertEqual(data['processing'], 5)

    def test_calculate_aggregate_tiers(self):
        """Test aggregate tier calculation logic."""
        from user_request_queue_svc import calculate_aggregate_tiers
        
        # Test data with both INVEST and WITHDRAW
        test_requests = [
            {'purpose': 'INVEST', 'tier1': 1000.0, 'tier2': 2000.0, 'tier3': 500.0},
            {'purpose': 'WITHDRAW', 'tier1': 300.0, 'tier2': 600.0, 'tier3': 150.0},
            {'purpose': 'INVEST', 'tier1': 500.0, 'tier2': 1000.0, 'tier3': 250.0}
        ]
        
        T1, T2, T3 = calculate_aggregate_tiers(test_requests)
        
        # Expected: (1000 + 500) - 300 = 1200 for T1
        # Expected: (2000 + 1000) - 600 = 2400 for T2  
        # Expected: (500 + 250) - 150 = 600 for T3
        self.assertEqual(T1, 1200.0)
        self.assertEqual(T2, 2400.0)
        self.assertEqual(T3, 600.0)

    @patch('user_request_queue_svc.requests.post')
    def test_call_bank_asset_agent_success(self, mock_requests_post):
        """Test successful call to bank-asset-agent."""
        from user_request_queue_svc import call_bank_asset_agent
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'SUCCESS'}
        mock_requests_post.return_value = mock_response
        
        result = call_bank_asset_agent(1000.0, 2000.0, 500.0)
        
        self.assertEqual(result, 'SUCCESS')
        mock_requests_post.assert_called_once()

    @patch('user_request_queue_svc.requests.post')
    def test_call_bank_asset_agent_failure(self, mock_requests_post):
        """Test failed call to bank-asset-agent."""
        from user_request_queue_svc import call_bank_asset_agent
        
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_requests_post.return_value = mock_response
        
        result = call_bank_asset_agent(1000.0, 2000.0, 500.0)
        
        self.assertEqual(result, 'FAILED')

    def test_update_global_tier_variables(self):
        """Test step5 - update global tier variables."""
        from user_request_queue_svc import update_global_tier_variables, TIER1, TIER2, TIER3
        
        # Store original values
        original_tier1 = TIER1
        original_tier2 = TIER2
        original_tier3 = TIER3
        
        # Test tier changes
        tier_changes = {
            'T1': 1000.0,
            'T2': 2000.0,
            'T3': 500.0
        }
        
        result = update_global_tier_variables(tier_changes)
        
        self.assertTrue(result)
        # Check environment variables were updated
        self.assertEqual(os.environ['TIER1'], str(original_tier1 + 1000.0))
        self.assertEqual(os.environ['TIER2'], str(original_tier2 + 2000.0))
        self.assertEqual(os.environ['TIER3'], str(original_tier3 + 500.0))

    def test_update_global_tier_variables_negative_changes(self):
        """Test step5 - update global tier variables with negative changes."""
        from user_request_queue_svc import update_global_tier_variables, TIER1, TIER2, TIER3
        
        # Store original values
        original_tier1 = TIER1
        original_tier2 = TIER2
        original_tier3 = TIER3
        
        # Test negative tier changes (withdrawals)
        tier_changes = {
            'T1': -500.0,
            'T2': -1000.0,
            'T3': -250.0
        }
        
        result = update_global_tier_variables(tier_changes)
        
        self.assertTrue(result)
        # Check environment variables were updated with negative changes
        self.assertEqual(os.environ['TIER1'], str(original_tier1 - 500.0))
        self.assertEqual(os.environ['TIER2'], str(original_tier2 - 1000.0))
        self.assertEqual(os.environ['TIER3'], str(original_tier3 - 250.0))

    @patch('user_request_queue_svc.get_db_connection')
    def test_update_request_status(self, mock_db_connect):
        """Test updating request statuses in database."""
        from user_request_queue_svc import update_request_status
        
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        uuid_list = ['uuid-001', 'uuid-002', 'uuid-003']
        status = 'DONE'
        
        result = update_request_status(uuid_list, status)
        
        self.assertTrue(result)
        # Should call execute for each UUID
        self.assertEqual(mock_cursor.execute.call_count, len(uuid_list))
        mock_conn.commit.assert_called_once()

    def test_invalid_purpose_values(self):
        """Test queue addition with invalid purpose values."""
        queue_data = {
            "uuid": "test-uuid",
            "tier1": 1000.0,
            "tier2": 2000.0,
            "tier3": 500.0,
            "purpose": "INVALID_PURPOSE",
            "accountid": "1234567890"
        }
        
        response = self.app.post('/api/v1/queue', json=queue_data)
        
        # Should fail with invalid purpose
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'failed')
        self.assertIn('Invalid purpose', data['error'])

    @patch('user_request_queue_svc.get_db_connection')
    def test_negative_tier_values(self, mock_db_connect):
        """Test queue addition with negative tier values."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        queue_data = {
            "uuid": "test-uuid-negative",
            "tier1": -1000.0,
            "tier2": -2000.0,
            "tier3": -500.0,
            "purpose": "WITHDRAW",
            "accountid": "1234567890"
        }
        
        response = self.app.post('/api/v1/queue', json=queue_data)
        
        # Should succeed as negative values are valid for withdrawals
        self.assertEqual(response.status_code, 200)

    @patch('user_request_queue_svc.get_db_connection')
    def test_large_tier_values(self, mock_db_connect):
        """Test queue addition with large tier values."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        queue_data = {
            "uuid": "test-uuid-large",
            "tier1": 1000000.0,
            "tier2": 2000000.0,
            "tier3": 500000.0,
            "purpose": "INVEST",
            "accountid": "1234567890"
        }
        
        response = self.app.post('/api/v1/queue', json=queue_data)
        
        self.assertEqual(response.status_code, 200)

    @patch('user_request_queue_svc.get_db_connection')
    def test_get_pending_requests(self, mock_db_connect):
        """Test getting pending requests for batch processing."""
        from user_request_queue_svc import get_pending_requests
        
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock database response
        mock_requests = [
            {
                'uuid': 'uuid-001',
                'accountid': '1234567890',
                'tier1': 1000.0,
                'tier2': 2000.0,
                'tier3': 500.0,
                'purpose': 'INVEST'
            },
            {
                'uuid': 'uuid-002',
                'accountid': '1234567891',
                'tier1': 500.0,
                'tier2': 1000.0,
                'tier3': 250.0,
                'purpose': 'WITHDRAW'
            }
        ]
        mock_cursor.fetchall.return_value = mock_requests
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        result = get_pending_requests()
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['uuid'], 'uuid-001')
        self.assertEqual(result[1]['purpose'], 'WITHDRAW')

if __name__ == '__main__':
    print("🧪 Running User Request Queue Service Unit Tests")
    print("============================================================")
    unittest.main()