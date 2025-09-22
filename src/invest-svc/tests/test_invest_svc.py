"""
Unit tests for invest-svc microservice
"""

import unittest
from unittest.mock import patch, Mock
import json
import os
import sys

# Add parent directory to path to import the Flask app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from invest_svc import app

class TestInvestSvc(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        # Set environment variables for testing
        os.environ['USER_TIER_AGENT_URI'] = 'http://mock-tier-agent'
        os.environ['USER_PORTFOLIO_DB_URI'] = 'postgresql://test:test@localhost:5432/test'
        os.environ['BALANCE_READER_URI'] = 'http://mock-balance-reader'
        os.environ['REQUEST_TIMEOUT'] = '1'

    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {"status": "healthy"})

    def test_ready_endpoint(self):
        """Test readiness check endpoint."""
        with patch('invest_svc.get_db_connection') as mock_db:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_db.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            response = self.app.get('/ready')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.data), {"status": "ready"})

    @patch('invest_svc.requests.get')
    @patch('invest_svc.requests.post')
    @patch('invest_svc.get_db_connection')
    def test_invest_success(self, mock_db, mock_post, mock_get):
        """Test successful investment processing."""
        # Mock balance reader response
        mock_balance_response = Mock()
        mock_balance_response.status_code = 200
        mock_balance_response.json.return_value = {"balance": 10000}
        
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
                                 headers={'Authorization': 'Bearer test-token'},
                                 json={"account_number": "1234567890", "amount": 1000.0})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'done')
        self.assertEqual(data['total_invested'], 1000.0)

    def test_invest_invalid_data(self):
        """Test investment with invalid data."""
        response = self.app.post('/api/v1/invest',
                                 headers={'Authorization': 'Bearer test-token'},
                                 json={"account_number": "", "amount": 1000.0})
        self.assertEqual(response.status_code, 400)

    def test_invest_negative_amount(self):
        """Test investment with negative amount."""
        response = self.app.post('/api/v1/invest',
                                 headers={'Authorization': 'Bearer test-token'},
                                 json={"account_number": "1234567890", "amount": -100.0})
        self.assertEqual(response.status_code, 400)

    @patch('invest_svc.requests.get')
    def test_insufficient_balance(self, mock_get):
        """Test investment with insufficient balance."""
        mock_balance_response = Mock()
        mock_balance_response.status_code = 200
        mock_balance_response.json.return_value = {"balance": 100}  # Less than investment amount
        
        mock_get.return_value = mock_balance_response
        
        response = self.app.post('/api/v1/invest',
                                 headers={'Authorization': 'Bearer test-token'},
                                 json={"account_number": "1234567890", "amount": 1000.0})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("Insufficient balance", data['error'])

    @patch('invest_svc.get_db_connection')
    def test_get_portfolio_success(self, mock_db):
        """Test successful portfolio retrieval."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock portfolio data
        mock_portfolio = {
            'id': 'test-portfolio-id',
            'user_id': '1234567890',
            'total_value': 1000.0,
            'currency': 'USD',
            'tier1_allocation': 60.0,
            'tier2_allocation': 30.0,
            'tier3_allocation': 10.0,
            'tier1_value': 600.0,
            'tier2_value': 300.0,
            'tier3_value': 100.0,
            'created_at': '2024-01-01T10:00:00Z',
            'updated_at': '2024-01-01T10:00:00Z'
        }
        
        mock_cursor.fetchone.return_value = Mock(**mock_portfolio)
        
        response = self.app.get('/api/v1/portfolio/1234567890')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['user_id'], '1234567890')

    @patch('invest_svc.get_db_connection')
    def test_get_portfolio_not_found(self, mock_db):
        """Test portfolio not found."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        
        response = self.app.get('/api/v1/portfolio/1234567890')
        self.assertEqual(response.status_code, 404)

if __name__ == '__main__':
    print("🧪 Running Invest Service Unit Tests")
    print("=" * 60)
    
    unittest.main(verbosity=2)
    
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print("✅ Unit tests completed for invest-svc")
