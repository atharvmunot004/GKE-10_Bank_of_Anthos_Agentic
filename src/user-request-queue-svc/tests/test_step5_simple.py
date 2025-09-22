import unittest
from unittest.mock import patch, Mock
import os
import sys

# Add parent directory to path to import the Flask app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestStep5Simple(unittest.TestCase):
    def setUp(self):
        # Reset environment variables
        os.environ['TIER1'] = '1000000.0'
        os.environ['TIER2'] = '2000000.0'
        os.environ['TIER3'] = '500000.0'

    def tearDown(self):
        # Reset environment variables after each test
        os.environ['TIER1'] = '1000000.0'
        os.environ['TIER2'] = '2000000.0'
        os.environ['TIER3'] = '500000.0'

    def test_step5_update_global_tier_variables_positive_changes(self):
        """Test step5 - update global tier variables with positive changes."""
        from user_request_queue_svc import update_global_tier_variables
        
        # Reset environment variables for clean test
        os.environ['TIER1'] = '1000000.0'
        os.environ['TIER2'] = '2000000.0'
        os.environ['TIER3'] = '500000.0'
        
        tier_changes = {'T1': 1000.0, 'T2': 2000.0, 'T3': 500.0}
        
        result = update_global_tier_variables(tier_changes)
        
        self.assertTrue(result)
        self.assertEqual(os.environ['TIER1'], '1001000.0')
        self.assertEqual(os.environ['TIER2'], '2002000.0')
        self.assertEqual(os.environ['TIER3'], '500500.0')

    def test_step5_update_global_tier_variables_negative_changes(self):
        """Test step5 - update global tier variables with negative changes."""
        from user_request_queue_svc import update_global_tier_variables
        
        # Reset environment variables for clean test
        os.environ['TIER1'] = '1000000.0'
        os.environ['TIER2'] = '2000000.0'
        os.environ['TIER3'] = '500000.0'
        
        tier_changes = {'T1': -500.0, 'T2': -1000.0, 'T3': -250.0}
        
        result = update_global_tier_variables(tier_changes)
        
        self.assertTrue(result)
        self.assertEqual(os.environ['TIER1'], '999500.0')
        self.assertEqual(os.environ['TIER2'], '1999000.0')
        self.assertEqual(os.environ['TIER3'], '499750.0')

    def test_step5_update_global_tier_variables_zero_changes(self):
        """Test step5 - update global tier variables with zero changes."""
        from user_request_queue_svc import update_global_tier_variables
        
        # Reset environment variables for clean test
        os.environ['TIER1'] = '1000000.0'
        os.environ['TIER2'] = '2000000.0'
        os.environ['TIER3'] = '500000.0'
        
        tier_changes = {'T1': 0.0, 'T2': 0.0, 'T3': 0.0}
        
        result = update_global_tier_variables(tier_changes)
        
        self.assertTrue(result)
        self.assertEqual(os.environ['TIER1'], '1000000.0')
        self.assertEqual(os.environ['TIER2'], '2000000.0')
        self.assertEqual(os.environ['TIER3'], '500000.0')

    def test_step5_calculate_aggregate_tiers_invest_only(self):
        """Test step5 - calculate aggregate tiers with INVEST only."""
        from user_request_queue_svc import calculate_aggregate_tiers
        
        requests = [
            {'purpose': 'INVEST', 'tier1': 1000.0, 'tier2': 2000.0, 'tier3': 500.0},
            {'purpose': 'INVEST', 'tier1': 500.0, 'tier2': 1000.0, 'tier3': 250.0},
        ]
        
        T1, T2, T3 = calculate_aggregate_tiers(requests)
        
        self.assertEqual(T1, 1500.0)
        self.assertEqual(T2, 3000.0)
        self.assertEqual(T3, 750.0)

    def test_step5_calculate_aggregate_tiers_withdraw_only(self):
        """Test step5 - calculate aggregate tiers with WITHDRAW only."""
        from user_request_queue_svc import calculate_aggregate_tiers
        
        requests = [
            {'purpose': 'WITHDRAW', 'tier1': 1000.0, 'tier2': 2000.0, 'tier3': 500.0},
            {'purpose': 'WITHDRAW', 'tier1': 500.0, 'tier2': 1000.0, 'tier3': 250.0},
        ]
        
        T1, T2, T3 = calculate_aggregate_tiers(requests)
        
        self.assertEqual(T1, -1500.0)
        self.assertEqual(T2, -3000.0)
        self.assertEqual(T3, -750.0)

    def test_step5_calculate_aggregate_tiers_mixed(self):
        """Test step5 - calculate aggregate tiers with mixed INVEST/WITHDRAW."""
        from user_request_queue_svc import calculate_aggregate_tiers
        
        requests = [
            {'purpose': 'INVEST', 'tier1': 1000.0, 'tier2': 2000.0, 'tier3': 500.0},
            {'purpose': 'WITHDRAW', 'tier1': 300.0, 'tier2': 600.0, 'tier3': 150.0},
            {'purpose': 'INVEST', 'tier1': 500.0, 'tier2': 1000.0, 'tier3': 250.0},
        ]
        
        T1, T2, T3 = calculate_aggregate_tiers(requests)
        
        # Expected: (1000 + 500) - 300 = 1200 for T1
        # Expected: (2000 + 1000) - 600 = 2400 for T2  
        # Expected: (500 + 250) - 150 = 600 for T3
        self.assertEqual(T1, 1200.0)
        self.assertEqual(T2, 2400.0)
        self.assertEqual(T3, 600.0)

    def test_step5_process_batch_with_successful_agent_response(self):
        """Test step5 - process batch with successful bank-asset-agent response."""
        from user_request_queue_svc import process_batch
        
        # Mock the global variables to reset them
        import user_request_queue_svc
        user_request_queue_svc.TIER1 = 1000000.0
        user_request_queue_svc.TIER2 = 2000000.0
        user_request_queue_svc.TIER3 = 500000.0
        
        with patch('user_request_queue_svc.get_db_connection') as mock_db_connect, \
             patch('user_request_queue_svc.requests.post') as mock_requests_post:
            
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
                    'tier1': 100.0,
                    'tier2': 200.0,
                    'tier3': 50.0,
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
            
            # Mock successful bank-asset-agent response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'status': 'SUCCESS'}
            mock_requests_post.return_value = mock_response
            
            # Run batch processing
            process_batch()
            
            # Verify bank-asset-agent was called
            mock_requests_post.assert_called_once()
            
            # Verify tier values were updated (step5)
            # Expected: 10 * (100,200,50) = (1000, 2000, 500)
            self.assertEqual(user_request_queue_svc.TIER1, 1001000.0)
            self.assertEqual(user_request_queue_svc.TIER2, 2002000.0)
            self.assertEqual(user_request_queue_svc.TIER3, 500500.0)

    def test_step5_process_batch_with_failed_agent_response(self):
        """Test step5 - process batch with failed bank-asset-agent response."""
        from user_request_queue_svc import process_batch
        
        # Mock the global variables to reset them
        import user_request_queue_svc
        user_request_queue_svc.TIER1 = 1000000.0
        user_request_queue_svc.TIER2 = 2000000.0
        user_request_queue_svc.TIER3 = 500000.0
        
        with patch('user_request_queue_svc.get_db_connection') as mock_db_connect, \
             patch('user_request_queue_svc.requests.post') as mock_requests_post:
            
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
                    'tier1': 100.0,
                    'tier2': 200.0,
                    'tier3': 50.0,
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
            
            # Run batch processing
            process_batch()
            
            # Verify bank-asset-agent was called
            mock_requests_post.assert_called_once()
            
            # Verify tier values were NOT updated (step5 should not trigger)
            self.assertEqual(user_request_queue_svc.TIER1, 1000000.0)
            self.assertEqual(user_request_queue_svc.TIER2, 2000000.0)
            self.assertEqual(user_request_queue_svc.TIER3, 500000.0)

if __name__ == '__main__':
    print("🔧 Running Simple Step 5 Tests")
    print("============================================================")
    unittest.main()
