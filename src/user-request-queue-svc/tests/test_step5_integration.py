import unittest
from unittest.mock import patch, Mock, MagicMock
import json
import os
import sys
from datetime import datetime

# Add parent directory to path to import the Flask app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from user_request_queue_svc import app

class TestStep5Integration(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        os.environ['QUEUE_DB_URI'] = 'postgresql://user:password@host:port/database'
        os.environ['BANK_ASSET_AGENT_URI'] = 'http://bank-asset-agent:8080'
        os.environ['BATCH_SIZE'] = '10'
        os.environ['REQUEST_TIMEOUT'] = '1'
        os.environ['POLLING_INTERVAL'] = '5'
        # Set initial tier values for testing
        os.environ['TIER1'] = '1000000.0'
        os.environ['TIER2'] = '2000000.0'
        os.environ['TIER3'] = '500000.0'
        
        # Store original values for cleanup
        self.original_tier1 = os.environ.get('TIER1', '1000000.0')
        self.original_tier2 = os.environ.get('TIER2', '2000000.0')
        self.original_tier3 = os.environ.get('TIER3', '500000.0')

    def tearDown(self):
        # Reset environment variables after each test
        os.environ['TIER1'] = self.original_tier1
        os.environ['TIER2'] = self.original_tier2
        os.environ['TIER3'] = self.original_tier3

    @patch('user_request_queue_svc.get_db_connection')
    @patch('user_request_queue_svc.requests.post')
    def test_step5_successful_batch_processing(self, mock_requests_post, mock_db_connect):
        """Test step5 - successful batch processing with tier variable updates."""
        from user_request_queue_svc import process_batch
        
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock pending requests (10 requests to trigger batch processing)
        mock_requests = []
        for i in range(10):
            mock_requests.append({
                'uuid': f'uuid-{i:03d}',
                'accountid': f'123456789{i}',
                'tier1': 100.0,
                'tier2': 200.0,
                'tier3': 50.0,
                'purpose': 'INVEST' if i % 2 == 0 else 'WITHDRAW'
            })
        
        # Mock database operations
        def mock_fetchall(*args, **kwargs):
            query = args[0] if args else ""
            if 'SELECT uuid' in str(query):
                return mock_requests
            return []
        
        mock_cursor.fetchall.side_effect = mock_fetchall
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        # Mock successful bank-asset-agent response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'SUCCESS'}
        mock_requests_post.return_value = mock_response
        
        # Store initial tier values
        initial_tier1 = float(os.environ.get('TIER1', '1000000.0'))
        initial_tier2 = float(os.environ.get('TIER2', '2000000.0'))
        initial_tier3 = float(os.environ.get('TIER3', '500000.0'))
        
        # Run batch processing
        process_batch()
        
        # Verify bank-asset-agent was called
        mock_requests_post.assert_called_once()
        
        # Verify tier values were updated (step5)
        # Expected aggregate: 5 INVEST * (100,200,50) - 5 WITHDRAW * (100,200,50) = (0,0,0)
        # So tier values should remain the same
        self.assertEqual(os.environ['TIER1'], str(initial_tier1))
        self.assertEqual(os.environ['TIER2'], str(initial_tier2))
        self.assertEqual(os.environ['TIER3'], str(initial_tier3))

    @patch('user_request_queue_svc.get_db_connection')
    @patch('user_request_queue_svc.requests.post')
    def test_step5_net_investment_increases_tier_values(self, mock_requests_post, mock_db_connect):
        """Test step5 - net investment increases tier values."""
        from user_request_queue_svc import process_batch
        
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock pending requests with net investment (more INVEST than WITHDRAW)
        mock_requests = []
        # 7 INVEST requests
        for i in range(7):
            mock_requests.append({
                'uuid': f'invest-{i:03d}',
                'accountid': f'123456789{i}',
                'tier1': 1000.0,
                'tier2': 2000.0,
                'tier3': 500.0,
                'purpose': 'INVEST'
            })
        # 3 WITHDRAW requests
        for i in range(3):
            mock_requests.append({
                'uuid': f'withdraw-{i:03d}',
                'accountid': f'123456789{i+7}',
                'tier1': 500.0,
                'tier2': 1000.0,
                'tier3': 250.0,
                'purpose': 'WITHDRAW'
            })
        
        # Mock database operations
        def mock_fetchall(*args, **kwargs):
            query = args[0] if args else ""
            if 'SELECT uuid' in str(query):
                return mock_requests
            return []
        
        mock_cursor.fetchall.side_effect = mock_fetchall
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        # Mock successful bank-asset-agent response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'SUCCESS'}
        mock_requests_post.return_value = mock_response
        
        # Store initial tier values
        initial_tier1 = float(os.environ.get('TIER1', '1000000.0'))
        initial_tier2 = float(os.environ.get('TIER2', '2000000.0'))
        initial_tier3 = float(os.environ.get('TIER3', '500000.0'))
        
        # Run batch processing
        process_batch()
        
        # Verify tier values were updated (step5)
        # Expected: 7 * (1000,2000,500) - 3 * (500,1000,250) = (5500, 11000, 2750)
        expected_tier1 = initial_tier1 + 5500.0
        expected_tier2 = initial_tier2 + 11000.0
        expected_tier3 = initial_tier3 + 2750.0
        
        self.assertEqual(os.environ['TIER1'], str(expected_tier1))
        self.assertEqual(os.environ['TIER2'], str(expected_tier2))
        self.assertEqual(os.environ['TIER3'], str(expected_tier3))

    @patch('user_request_queue_svc.get_db_connection')
    @patch('user_request_queue_svc.requests.post')
    def test_step5_net_withdrawal_decreases_tier_values(self, mock_requests_post, mock_db_connect):
        """Test step5 - net withdrawal decreases tier values."""
        from user_request_queue_svc import process_batch
        
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock pending requests with net withdrawal (more WITHDRAW than INVEST)
        mock_requests = []
        # 3 INVEST requests
        for i in range(3):
            mock_requests.append({
                'uuid': f'invest-{i:03d}',
                'accountid': f'123456789{i}',
                'tier1': 1000.0,
                'tier2': 2000.0,
                'tier3': 500.0,
                'purpose': 'INVEST'
            })
        # 7 WITHDRAW requests
        for i in range(7):
            mock_requests.append({
                'uuid': f'withdraw-{i:03d}',
                'accountid': f'123456789{i+3}',
                'tier1': 1000.0,
                'tier2': 2000.0,
                'tier3': 500.0,
                'purpose': 'WITHDRAW'
            })
        
        # Mock database operations
        def mock_fetchall(*args, **kwargs):
            query = args[0] if args else ""
            if 'SELECT uuid' in str(query):
                return mock_requests
            return []
        
        mock_cursor.fetchall.side_effect = mock_fetchall
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        # Mock successful bank-asset-agent response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'SUCCESS'}
        mock_requests_post.return_value = mock_response
        
        # Store initial tier values
        initial_tier1 = float(os.environ.get('TIER1', '1000000.0'))
        initial_tier2 = float(os.environ.get('TIER2', '2000000.0'))
        initial_tier3 = float(os.environ.get('TIER3', '500000.0'))
        
        # Run batch processing
        process_batch()
        
        # Verify tier values were updated (step5)
        # Expected: 3 * (1000,2000,500) - 7 * (1000,2000,500) = (-4000, -8000, -2000)
        expected_tier1 = initial_tier1 - 4000.0
        expected_tier2 = initial_tier2 - 8000.0
        expected_tier3 = initial_tier3 - 2000.0
        
        self.assertEqual(os.environ['TIER1'], str(expected_tier1))
        self.assertEqual(os.environ['TIER2'], str(expected_tier2))
        self.assertEqual(os.environ['TIER3'], str(expected_tier3))

    @patch('user_request_queue_svc.get_db_connection')
    @patch('user_request_queue_svc.requests.post')
    def test_step5_failed_bank_agent_no_tier_update(self, mock_requests_post, mock_db_connect):
        """Test step5 - failed bank-asset-agent response does not update tier values."""
        from user_request_queue_svc import process_batch
        
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock pending requests
        mock_requests = []
        for i in range(10):
            mock_requests.append({
                'uuid': f'uuid-{i:03d}',
                'accountid': f'123456789{i}',
                'tier1': 1000.0,
                'tier2': 2000.0,
                'tier3': 500.0,
                'purpose': 'INVEST'
            })
        
        # Mock database operations
        def mock_fetchall(*args, **kwargs):
            query = args[0] if args else ""
            if 'SELECT uuid' in str(query):
                return mock_requests
            return []
        
        mock_cursor.fetchall.side_effect = mock_fetchall
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        # Mock failed bank-asset-agent response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'FAILED'}
        mock_requests_post.return_value = mock_response
        
        # Store initial tier values
        initial_tier1 = float(os.environ.get('TIER1', '1000000.0'))
        initial_tier2 = float(os.environ.get('TIER2', '2000000.0'))
        initial_tier3 = float(os.environ.get('TIER3', '500000.0'))
        
        # Run batch processing
        process_batch()
        
        # Verify tier values were NOT updated (step5 should not trigger)
        self.assertEqual(os.environ['TIER1'], str(initial_tier1))
        self.assertEqual(os.environ['TIER2'], str(initial_tier2))
        self.assertEqual(os.environ['TIER3'], str(initial_tier3))

    @patch('user_request_queue_svc.get_db_connection')
    def test_step5_insufficient_requests_no_processing(self, mock_db_connect):
        """Test that insufficient requests do not trigger batch processing."""
        from user_request_queue_svc import process_batch
        
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock insufficient requests (less than BATCH_SIZE)
        mock_requests = []
        for i in range(5):  # Only 5 requests, need 10 for batch processing
            mock_requests.append({
                'uuid': f'uuid-{i:03d}',
                'accountid': f'123456789{i}',
                'tier1': 1000.0,
                'tier2': 2000.0,
                'tier3': 500.0,
                'purpose': 'INVEST'
            })
        
        # Mock database operations
        def mock_fetchall(*args, **kwargs):
            query = args[0] if args else ""
            if 'SELECT uuid' in str(query):
                return mock_requests
            return []
        
        mock_cursor.fetchall.side_effect = mock_fetchall
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        # Store initial tier values
        initial_tier1 = float(os.environ.get('TIER1', '1000000.0'))
        initial_tier2 = float(os.environ.get('TIER2', '2000000.0'))
        initial_tier3 = float(os.environ.get('TIER3', '500000.0'))
        
        # Run batch processing
        process_batch()
        
        # Verify tier values were NOT updated (no batch processing occurred)
        self.assertEqual(os.environ['TIER1'], str(initial_tier1))
        self.assertEqual(os.environ['TIER2'], str(initial_tier2))
        self.assertEqual(os.environ['TIER3'], str(initial_tier3))

    def test_step5_different_success_statuses(self):
        """Test step5 triggers on different success status values."""
        from user_request_queue_svc import update_global_tier_variables
        
        # Reset environment variables for clean test
        os.environ['TIER1'] = '1000000.0'
        os.environ['TIER2'] = '2000000.0'
        os.environ['TIER3'] = '500000.0'
        
        # Test with SUCCESS status
        tier_changes = {'T1': 1000.0, 'T2': 2000.0, 'T3': 500.0}
        initial_tier1 = float(os.environ.get('TIER1', '1000000.0'))
        
        result = update_global_tier_variables(tier_changes)
        self.assertTrue(result)
        self.assertEqual(os.environ['TIER1'], str(initial_tier1 + 1000.0))
        
        # Reset for next test
        os.environ['TIER1'] = '1000000.0'
        os.environ['TIER2'] = '2000000.0'
        os.environ['TIER3'] = '500000.0'
        
        # Test with DONE status (should work the same way)
        result = update_global_tier_variables(tier_changes)
        self.assertTrue(result)
        self.assertEqual(os.environ['TIER1'], str(initial_tier1 + 1000.0))

    def test_step5_edge_cases(self):
        """Test step5 with edge cases."""
        from user_request_queue_svc import update_global_tier_variables
        
        # Reset environment variables for clean test
        os.environ['TIER1'] = '1000000.0'
        os.environ['TIER2'] = '2000000.0'
        os.environ['TIER3'] = '500000.0'
        
        # Test with zero changes
        tier_changes = {'T1': 0.0, 'T2': 0.0, 'T3': 0.0}
        initial_tier1 = float(os.environ.get('TIER1', '1000000.0'))
        
        result = update_global_tier_variables(tier_changes)
        self.assertTrue(result)
        self.assertEqual(os.environ['TIER1'], str(initial_tier1))
        
        # Test with very large changes
        tier_changes = {'T1': 1000000.0, 'T2': 2000000.0, 'T3': 500000.0}
        result = update_global_tier_variables(tier_changes)
        self.assertTrue(result)
        self.assertEqual(os.environ['TIER1'], str(initial_tier1 + 1000000.0))

if __name__ == '__main__':
    print("🔗 Running Step 5 Integration Tests")
    print("============================================================")
    unittest.main()
