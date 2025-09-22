import unittest
from unittest.mock import patch, Mock
import json
import os
import sys
from datetime import datetime

# Add parent directory to path to import the Flask app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from portfolio_reader import app

class TestPortfolioReader(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        os.environ['USER_PORTFOLIO_DB_URI'] = 'postgresql://user:password@host:port/database'

    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {"status": "healthy"})

    @patch('portfolio_reader.psycopg2.connect')
    def test_ready_endpoint_success(self, mock_connect):
        """Test readiness check endpoint with successful database connection."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        response = self.app.get('/ready')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {"status": "ready"})
        mock_cursor.execute.assert_called_with("SELECT 1")

    @patch('portfolio_reader.psycopg2.connect')
    def test_ready_endpoint_failure(self, mock_connect):
        """Test readiness check endpoint with database connection failure."""
        mock_connect.side_effect = Exception("Database connection failed")
        
        response = self.app.get('/ready')
        self.assertEqual(response.status_code, 500)
        self.assertIn("not ready", json.loads(response.data)["status"])

    @patch('portfolio_reader.psycopg2.connect')
    def test_get_portfolio_success(self, mock_connect):
        """Test successful portfolio retrieval."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
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
        
        # Mock transaction data
        transaction_data = {
            'id': '550e8400-e29b-41d4-a716-446655440000',
            'accountid': '1234567890',
            'transaction_type': 'INVEST',
            'tier1_change': 600.0,
            'tier2_change': 300.0,
            'tier3_change': 100.0,
            'total_amount': 1000.0,
            'fees': 0.0,
            'status': 'COMPLETED',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        mock_cursor.fetchone.side_effect = [portfolio_data]
        mock_cursor.fetchall.return_value = [transaction_data]
        
        response = self.app.get('/api/v1/portfolio/1234567890')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('portfolio', data)
        self.assertIn('transactions', data)
        self.assertEqual(data['portfolio']['accountid'], '1234567890')

    @patch('portfolio_reader.psycopg2.connect')
    def test_get_portfolio_not_found(self, mock_connect):
        """Test portfolio retrieval when portfolio doesn't exist."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = None
        
        response = self.app.get('/api/v1/portfolio/9999999999')
        self.assertEqual(response.status_code, 404)
        self.assertIn('not found', json.loads(response.data)['error'])

    @patch('portfolio_reader.psycopg2.connect')
    def test_get_portfolio_transactions_success(self, mock_connect):
        """Test successful transaction retrieval."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock portfolio exists check
        portfolio_data = {'accountid': '1234567890'}
        transaction_data = {
            'id': '550e8400-e29b-41d4-a716-446655440000',
            'accountid': '1234567890',
            'transaction_type': 'INVEST',
            'tier1_change': 600.0,
            'tier2_change': 300.0,
            'tier3_change': 100.0,
            'total_amount': 1000.0,
            'fees': 0.0,
            'status': 'COMPLETED',
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
        # Updated format: transactions are arrays, not objects
        # Format: [uuid, accountid, tier1_change, tier2_change, tier3_change, status, ...]
        transaction = data[0]
        self.assertIsInstance(transaction, list)
        self.assertEqual(transaction[0], '550e8400-e29b-41d4-a716-446655440000')  # uuid
        self.assertEqual(transaction[1], '1234567890')  # accountid
        self.assertEqual(transaction[5], 'COMPLETED')  # status

    @patch('portfolio_reader.psycopg2.connect')
    def test_get_portfolio_transactions_with_pagination(self, mock_connect):
        """Test transaction retrieval with pagination parameters."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        portfolio_data = {'accountid': '1234567890'}
        mock_cursor.fetchone.return_value = portfolio_data
        mock_cursor.fetchall.return_value = []
        
        response = self.app.get('/api/v1/portfolio/1234567890/transactions?limit=20&offset=10')
        self.assertEqual(response.status_code, 200)
        
        # Verify the query was called with pagination parameters
        calls = mock_cursor.execute.call_args_list
        transaction_call = calls[-1]  # Last call should be the transaction query
        self.assertIn('LIMIT %s OFFSET %s', str(transaction_call))

    @patch('portfolio_reader.psycopg2.connect')
    def test_get_portfolio_summary_success(self, mock_connect):
        """Test successful portfolio summary retrieval."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
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
        
        # Mock invested amount
        invested_data = {'total_invested': 9500.0}
        
        # Mock transaction stats
        stats_data = {
            'total_transactions': 5,
            'invest_count': 4,
            'withdrawal_count': 1,
            'completed_count': 5
        }
        
        mock_cursor.fetchone.side_effect = [portfolio_data, invested_data, stats_data]
        
        response = self.app.get('/api/v1/portfolio/1234567890/summary')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('current_value', data)
        self.assertIn('allocation', data)
        self.assertIn('analytics', data)
        self.assertEqual(data['analytics']['total_invested'], 9500.0)
        self.assertEqual(data['analytics']['gain_loss_percentage'], 5.26)

    @patch('portfolio_reader.psycopg2.connect')
    def test_get_portfolio_summary_not_found(self, mock_connect):
        """Test portfolio summary when portfolio doesn't exist."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = None
        
        response = self.app.get('/api/v1/portfolio/9999999999/summary')
        self.assertEqual(response.status_code, 404)
        self.assertIn('not found', json.loads(response.data)['error'])

    @patch('portfolio_reader.psycopg2.connect')
    def test_database_error_handling(self, mock_connect):
        """Test database error handling."""
        mock_connect.side_effect = Exception("Database error")
        
        response = self.app.get('/api/v1/portfolio/1234567890')
        self.assertEqual(response.status_code, 500)
        self.assertIn('error', json.loads(response.data))

if __name__ == '__main__':
    unittest.main()
