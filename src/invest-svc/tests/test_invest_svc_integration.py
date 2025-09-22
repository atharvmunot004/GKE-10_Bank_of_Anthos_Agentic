import unittest
from unittest.mock import patch, Mock
import json
import os
import sys
from datetime import datetime

# Add parent directory to path to import the Flask app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from invest_svc import app, update_portfolio_allocations, create_portfolio_transaction, get_tier_allocation, check_balance

class TestInvestSvcIntegration(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        os.environ['USER_PORTFOLIO_DB_URI'] = 'postgresql://user:password@host:port/database'
        os.environ['USER_TIER_AGENT_URI'] = 'http://mock-user-tier-agent'
        os.environ['BALANCE_READER_URI'] = 'http://mock-balance-reader'
        os.environ['REQUEST_TIMEOUT'] = '1'

    @patch('invest_svc.requests.get')
    def test_check_balance_success(self, mock_get):
        """Test balance check functionality."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"balance": 5000.0}
        mock_get.return_value = mock_response
        
        result = check_balance("1234567890", 1000.0, {"Authorization": "Bearer test-token"})
        self.assertTrue(result)
        
        # Test insufficient balance
        result = check_balance("1234567890", 10000.0, {"Authorization": "Bearer test-token"})
        self.assertFalse(result)

    @patch('invest_svc.requests.post')
    def test_get_tier_allocation_success(self, mock_post):
        """Test tier allocation functionality."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "accountid": "1234567890",
            "amount": 1000.0,
            "uuid": "test-uuid-123",
            "tier1": 600.0,
            "tier2": 300.0,
            "tier3": 100.0
        }
        mock_post.return_value = mock_response
        
        result = get_tier_allocation("1234567890", 1000.0, {"Authorization": "Bearer test-token"})
        
        self.assertEqual(result['accountid'], "1234567890")
        self.assertEqual(result['amount'], 1000.0)
        self.assertEqual(result['tier1'], 600.0)
        self.assertEqual(result['tier2'], 300.0)
        self.assertEqual(result['tier3'], 100.0)

    @patch('invest_svc.get_db_connection')
    def test_update_portfolio_allocations_new_portfolio(self, mock_db_connect):
        """Test creating new portfolio with allocations."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock no existing portfolio
        mock_cursor.fetchone.return_value = None
        
        tier_data = {
            "accountid": "1234567890",
            "tier1": 600.0,
            "tier2": 300.0,
            "tier3": 100.0
        }
        
        result = update_portfolio_allocations("1234567890", tier_data)
        
        self.assertTrue(result)
        # Verify INSERT was called
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()

    @patch('invest_svc.get_db_connection')
    def test_update_portfolio_allocations_existing_portfolio(self, mock_db_connect):
        """Test updating existing portfolio allocations."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock existing portfolio
        existing_portfolio = {
            'accountid': '1234567890',
            'tier1_allocation': 500.0,
            'tier2_allocation': 250.0,
            'tier3_allocation': 250.0
        }
        mock_cursor.fetchone.return_value = existing_portfolio
        
        tier_data = {
            "accountid": "1234567890",
            "tier1": 300.0,
            "tier2": 150.0,
            "tier3": 50.0
        }
        
        result = update_portfolio_allocations("1234567890", tier_data)
        
        self.assertTrue(result)
        # Verify UPDATE was called
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()

    @patch('invest_svc.get_db_connection')
    def test_create_portfolio_transaction(self, mock_db_connect):
        """Test creating portfolio transaction."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        tier_data = {
            "tier1": 600.0,
            "tier2": 300.0,
            "tier3": 100.0
        }
        
        result = create_portfolio_transaction("1234567890", 1000.0, tier_data, "test-uuid")
        
        self.assertIsNotNone(result)
        # Verify INSERT was called
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()

    @patch('invest_svc.requests.get')
    @patch('invest_svc.requests.post')
    @patch('invest_svc.get_db_connection')
    def test_complete_investment_flow(self, mock_db, mock_post, mock_get):
        """Test complete investment flow from start to finish."""
        # Mock balance check
        mock_balance_response = Mock()
        mock_balance_response.status_code = 200
        mock_balance_response.json.return_value = {"balance": 10000.0}
        
        # Mock tier allocation
        mock_tier_response = Mock()
        mock_tier_response.status_code = 200
        mock_tier_response.json.return_value = {
            "accountid": "1234567890",
            "amount": 1000.0,
            "uuid": "test-uuid-complete",
            "tier1": 600.0,
            "tier2": 300.0,
            "tier3": 100.0
        }
        
        mock_get.return_value = mock_balance_response
        mock_post.return_value = mock_tier_response
        
        # Mock database operations
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None  # No existing portfolio
        
        response = self.app.post('/api/v1/invest',
                                 headers={'x-auth-account-id': '1234567890', 'Authorization': 'Bearer test-token'},
                                 json={"amount": 1000.0})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Verify response structure
        self.assertEqual(data['status'], 'done')
        self.assertEqual(data['accountid'], '1234567890')
        self.assertEqual(data['amount'], 1000.0)
        self.assertEqual(data['uuid'], 'test-uuid-complete')
        self.assertEqual(data['tier1'], 600.0)
        self.assertEqual(data['tier2'], 300.0)
        self.assertEqual(data['tier3'], 100.0)
        self.assertIn('transaction_id', data)
        
        # Verify external service calls were made (checking that calls were made, not exact parameters)
        self.assertTrue(mock_get.called)
        self.assertTrue(mock_post.called)
        
        # Verify the calls were made with correct URLs
        get_calls = mock_get.call_args_list
        post_calls = mock_post.call_args_list
        
        self.assertIn('/balances/1234567890', str(get_calls))
        self.assertIn('/allocate', str(post_calls))

    @patch('invest_svc.requests.get')
    @patch('invest_svc.requests.post')
    @patch('invest_svc.get_db_connection')
    def test_investment_with_existing_portfolio(self, mock_db, mock_post, mock_get):
        """Test investment when portfolio already exists."""
        # Mock balance check
        mock_balance_response = Mock()
        mock_balance_response.status_code = 200
        mock_balance_response.json.return_value = {"balance": 10000.0}
        
        # Mock tier allocation
        mock_tier_response = Mock()
        mock_tier_response.status_code = 200
        mock_tier_response.json.return_value = {
            "accountid": "1234567890",
            "amount": 500.0,
            "uuid": "test-uuid-existing",
            "tier1": 300.0,
            "tier2": 150.0,
            "tier3": 50.0
        }
        
        mock_get.return_value = mock_balance_response
        mock_post.return_value = mock_tier_response
        
        # Mock existing portfolio
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        existing_portfolio = {
            'accountid': '1234567890',
            'tier1_allocation': 600.0,
            'tier2_allocation': 300.0,
            'tier3_allocation': 100.0
        }
        mock_cursor.fetchone.return_value = existing_portfolio
        
        response = self.app.post('/api/v1/invest',
                                 headers={'x-auth-account-id': '1234567890', 'Authorization': 'Bearer test-token'},
                                 json={"amount": 500.0})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'done')
        
        # Verify database operations were called
        self.assertTrue(mock_cursor.execute.called)
        self.assertTrue(mock_conn.commit.called)

if __name__ == '__main__':
    print("🧪 Running Invest Service Integration Tests")
    print("============================================================")
    unittest.main()
