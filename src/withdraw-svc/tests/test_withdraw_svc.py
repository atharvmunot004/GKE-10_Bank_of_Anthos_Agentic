import unittest
from unittest.mock import patch, Mock
import json
import os
import sys
from datetime import datetime

# Add parent directory to path to import the Flask app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from withdraw_svc import app

class TestWithdrawSvc(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        os.environ['USER_PORTFOLIO_DB_URI'] = 'postgresql://user:password@host:port/database'
        os.environ['USER_TIER_AGENT_URI'] = 'http://mock-user-tier-agent'
        os.environ['REQUEST_TIMEOUT'] = '1'

    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {"status": "healthy"})

    @patch('withdraw_svc.requests.get')
    @patch('withdraw_svc.get_db_connection')
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

    @patch('withdraw_svc.requests.post')
    @patch('withdraw_svc.get_db_connection')
    def test_withdraw_success(self, mock_db, mock_post):
        """Test successful withdrawal processing."""
        # Mock database operations
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock tier agent response
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
        mock_post.return_value = mock_tier_response
        
        # Mock database operations in sequence
        def mock_fetchone_side_effect(*args):
            if len(mock_cursor.fetchone.side_effect) == 0:
                # First call - portfolio value check
                return {'total_value': 10000.0}
            elif len(mock_cursor.fetchone.side_effect) == 1:
                # Second call - current portfolio values for update
                return {'tier1_value': 6000.0, 'tier2_value': 3000.0, 'tier3_value': 1000.0, 'total_value': 10000.0}
            else:
                # Third call - transaction ID return
                return ('transaction-uuid',)
        
        mock_cursor.fetchone.side_effect = [
            {'total_value': 10000.0},  # Portfolio value check
            {'tier1_value': 6000.0, 'tier2_value': 3000.0, 'tier3_value': 1000.0, 'total_value': 10000.0},  # Current portfolio
        ]
        
        # Mock transaction ID return separately
        mock_cursor.fetchone.return_value = ('transaction-uuid',)
        
        response = self.app.post('/api/v1/withdraw',
                                 headers={'x-auth-account-id': '1234567890', 'Authorization': 'Bearer test-token'},
                                 json={"accountid": "1234567890", "amount": 1000.0})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'done')
        self.assertEqual(data['amount'], 1000.0)
        self.assertEqual(data['tier1'], 600.0)

    def test_withdraw_missing_account_id(self):
        """Test withdrawal without account ID."""
        response = self.app.post('/api/v1/withdraw',
                                 headers={'Authorization': 'Bearer test-token'},
                                 json={"amount": 1000.0})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'failed')

    def test_withdraw_invalid_amount(self):
        """Test withdrawal with invalid amount."""
        response = self.app.post('/api/v1/withdraw',
                                 headers={'x-auth-account-id': '1234567890', 'Authorization': 'Bearer test-token'},
                                 json={"accountid": "1234567890", "amount": -100.0})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'failed')

    @patch('withdraw_svc.get_db_connection')
    def test_withdraw_insufficient_funds(self, mock_db_connect):
        """Test withdrawal with insufficient funds."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock insufficient portfolio value
        mock_cursor.fetchone.return_value = {'total_value': 500.0}
        
        response = self.app.post('/api/v1/withdraw',
                                 headers={'x-auth-account-id': '1234567890', 'Authorization': 'Bearer test-token'},
                                 json={"accountid": "1234567890", "amount": 1000.0})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'failed')
        self.assertIn('Insufficient portfolio value', data['error'])

    @patch('withdraw_svc.requests.post')
    @patch('withdraw_svc.get_db_connection')
    def test_tier_agent_failure(self, mock_db_connect, mock_post):
        """Test withdrawal when tier agent fails."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock sufficient portfolio value
        mock_cursor.fetchone.return_value = {'total_value': 10000.0}
        
        # Mock tier agent failure
        mock_tier_response = Mock()
        mock_tier_response.status_code = 500
        mock_tier_response.text = "Tier agent error"
        mock_post.return_value = mock_tier_response
        
        response = self.app.post('/api/v1/withdraw',
                                 headers={'x-auth-account-id': '1234567890', 'Authorization': 'Bearer test-token'},
                                 json={"accountid": "1234567890", "amount": 1000.0})
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'failed')

    @patch('withdraw_svc.get_db_connection')
    def test_portfolio_not_found(self, mock_db_connect):
        """Test withdrawal when portfolio doesn't exist."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock portfolio not found
        mock_cursor.fetchone.return_value = None
        
        response = self.app.post('/api/v1/withdraw',
                                 headers={'x-auth-account-id': '1234567890', 'Authorization': 'Bearer test-token'},
                                 json={"accountid": "1234567890", "amount": 1000.0})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'failed')

    @patch('withdraw_svc.get_db_connection')
    def test_withdraw_without_headers(self, mock_db_connect):
        """Test withdrawal request without proper headers."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock portfolio not found
        mock_cursor.fetchone.return_value = None
        
        response = self.app.post('/api/v1/withdraw',
                                 json={"accountid": "1234567890", "amount": 1000.0})
        self.assertEqual(response.status_code, 400)

if __name__ == '__main__':
    print("🧪 Running Withdraw Service Unit Tests")
    print("============================================================")
    unittest.main()
