import unittest
from unittest.mock import patch, Mock
import json
import os
import sys
from datetime import datetime

# Add parent directory to path to import the Flask app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from invest_svc import app

class TestInvestSvc(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        os.environ['USER_PORTFOLIO_DB_URI'] = 'postgresql://user:password@host:port/database'
        os.environ['USER_TIER_AGENT_URI'] = 'http://mock-user-tier-agent'
        os.environ['BALANCE_READER_URI'] = 'http://mock-balance-reader'
        os.environ['REQUEST_TIMEOUT'] = '1'

    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {"status": "healthy"})

    @patch('invest_svc.requests.get')
    @patch('invest_svc.get_db_connection')
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

    @patch('invest_svc.requests.get')
    @patch('invest_svc.requests.post')
    @patch('invest_svc.get_db_connection')
    def test_invest_success(self, mock_db, mock_post, mock_get):
        """Test successful investment processing."""
        # Mock balance check response
        mock_balance_response = Mock()
        mock_balance_response.status_code = 200
        mock_balance_response.json.return_value = {"balance": 10000.0}
        
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
        self.assertEqual(data['status'], 'done')
        self.assertEqual(data['amount'], 1000.0)
        self.assertEqual(data['tier1'], 600.0)

    def test_invest_missing_account_id(self):
        """Test investment without account ID."""
        response = self.app.post('/api/v1/invest',
                                 headers={'Authorization': 'Bearer test-token'},
                                 json={"amount": 1000.0})
        self.assertEqual(response.status_code, 401)

    def test_invest_invalid_amount(self):
        """Test investment with invalid amount."""
        response = self.app.post('/api/v1/invest',
                                 headers={'x-auth-account-id': '1234567890', 'Authorization': 'Bearer test-token'},
                                 json={"amount": -100.0})
        self.assertEqual(response.status_code, 400)

    @patch('invest_svc.requests.get')
    def test_insufficient_balance(self, mock_get):
        """Test investment with insufficient balance."""
        mock_balance_response = Mock()
        mock_balance_response.status_code = 200
        mock_balance_response.json.return_value = {"balance": 500.0}  # Insufficient balance
        mock_get.return_value = mock_balance_response
        
        response = self.app.post('/api/v1/invest',
                                 headers={'x-auth-account-id': '1234567890', 'Authorization': 'Bearer test-token'},
                                 json={"amount": 1000.0})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'failed')

    @patch('invest_svc.requests.get')
    @patch('invest_svc.requests.post')
    def test_tier_agent_failure(self, mock_post, mock_get):
        """Test investment when tier agent fails."""
        # Mock successful balance check
        mock_balance_response = Mock()
        mock_balance_response.status_code = 200
        mock_balance_response.json.return_value = {"balance": 10000.0}
        mock_get.return_value = mock_balance_response
        
        # Mock tier agent failure
        mock_tier_response = Mock()
        mock_tier_response.status_code = 500
        mock_tier_response.text = "Tier agent error"
        mock_post.return_value = mock_tier_response
        
        response = self.app.post('/api/v1/invest',
                                 headers={'x-auth-account-id': '1234567890', 'Authorization': 'Bearer test-token'},
                                 json={"amount": 1000.0})
        
        self.assertEqual(response.status_code, 500)

    @patch('invest_svc.get_db_connection')
    def test_get_portfolio_success(self, mock_db_connect):
        """Test successful portfolio retrieval."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock portfolio data
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
        
        response = self.app.get('/api/v1/portfolio/1234567890')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['accountid'], '1234567890')
        self.assertEqual(data['total_value'], 10000.0)

    @patch('invest_svc.get_db_connection')
    def test_get_portfolio_not_found(self, mock_db_connect):
        """Test portfolio not found."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = None
        
        response = self.app.get('/api/v1/portfolio/9999999999')
        self.assertEqual(response.status_code, 404)
        self.assertIn('not found', json.loads(response.data)['error'])

    @patch('invest_svc.get_db_connection')
    def test_get_portfolio_transactions_success(self, mock_db_connect):
        """Test successful transaction retrieval."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock portfolio exists check
        portfolio_data = {'accountid': '1234567890'}
        transaction_data = {
            'id': '550e8400-e29b-41d4-a716-446655440000',
            'transaction_type': 'INVEST',
            'tier1_change': 600.0,
            'tier2_change': 300.0,
            'tier3_change': 100.0,
            'total_amount': 1000.0,
            'fees': 0.0,
            'status': 'PENDING',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        mock_cursor.fetchone.side_effect = [portfolio_data]
        mock_cursor.fetchall.return_value = [transaction_data]
        
        response = self.app.get('/api/v1/portfolio/1234567890/transactions')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['transaction_type'], 'INVEST')

    @patch('invest_svc.get_db_connection')
    def test_get_portfolio_transactions_not_found(self, mock_db_connect):
        """Test transaction retrieval when portfolio doesn't exist."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = None
        
        response = self.app.get('/api/v1/portfolio/9999999999/transactions')
        self.assertEqual(response.status_code, 404)
        self.assertIn('not found', json.loads(response.data)['error'])

if __name__ == '__main__':
    print("🧪 Running Invest Service Updated Unit Tests")
    print("============================================================")
    unittest.main()
