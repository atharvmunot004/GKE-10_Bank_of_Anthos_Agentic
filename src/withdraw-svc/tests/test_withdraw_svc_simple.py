import unittest
from unittest.mock import patch, Mock
import json
import os
import sys
from datetime import datetime

# Add parent directory to path to import the Flask app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from withdraw_svc import app

class TestWithdrawSvcSimple(unittest.TestCase):
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

    def test_withdraw_missing_data(self):
        """Test withdrawal with missing data."""
        response = self.app.post('/api/v1/withdraw',
                                 headers={'Authorization': 'Bearer test-token'},
                                 json={})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'failed')

    def test_withdraw_invalid_amount(self):
        """Test withdrawal with invalid amount."""
        response = self.app.post('/api/v1/withdraw',
                                 headers={'Authorization': 'Bearer test-token'},
                                 json={"accountid": "1234567890", "amount": -100.0})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'failed')

    @patch('withdraw_svc.check_portfolio_value')
    def test_withdraw_insufficient_funds(self, mock_check_value):
        """Test withdrawal with insufficient funds."""
        mock_check_value.return_value = 500.0
        
        response = self.app.post('/api/v1/withdraw',
                                 headers={'Authorization': 'Bearer test-token'},
                                 json={"accountid": "1234567890", "amount": 1000.0})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'failed')
        self.assertIn('Insufficient portfolio value', data['error'])

    @patch('withdraw_svc.update_portfolio_values')
    @patch('withdraw_svc.create_withdrawal_transaction')
    @patch('withdraw_svc.get_tier_allocation')
    @patch('withdraw_svc.check_portfolio_value')
    def test_withdraw_success(self, mock_check_value, mock_tier_allocation, 
                             mock_create_transaction, mock_update_portfolio):
        """Test successful withdrawal processing."""
        # Mock sufficient portfolio value
        mock_check_value.return_value = 10000.0
        
        # Mock tier allocation
        mock_tier_allocation.return_value = {
            "accountid": "1234567890",
            "amount": 1000.0,
            "uuid": "test-uuid",
            "tier1": 600.0,
            "tier2": 300.0,
            "tier3": 100.0
        }
        
        # Mock transaction creation
        mock_create_transaction.return_value = "transaction-uuid"
        
        # Mock portfolio update
        mock_update_portfolio.return_value = True
        
        response = self.app.post('/api/v1/withdraw',
                                 headers={'Authorization': 'Bearer test-token'},
                                 json={"accountid": "1234567890", "amount": 1000.0})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'done')
        self.assertEqual(data['amount'], 1000.0)
        self.assertEqual(data['tier1'], 600.0)
        self.assertEqual(data['tier2'], 300.0)
        self.assertEqual(data['tier3'], 100.0)

    @patch('withdraw_svc.get_tier_allocation')
    @patch('withdraw_svc.check_portfolio_value')
    def test_tier_agent_failure(self, mock_check_value, mock_tier_allocation):
        """Test withdrawal when tier agent fails."""
        mock_check_value.return_value = 10000.0
        mock_tier_allocation.side_effect = Exception("Tier allocation failed")
        
        response = self.app.post('/api/v1/withdraw',
                                 headers={'Authorization': 'Bearer test-token'},
                                 json={"accountid": "1234567890", "amount": 1000.0})
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'failed')

if __name__ == '__main__':
    print("🧪 Running Withdraw Service Simple Unit Tests")
    print("============================================================")
    unittest.main()
