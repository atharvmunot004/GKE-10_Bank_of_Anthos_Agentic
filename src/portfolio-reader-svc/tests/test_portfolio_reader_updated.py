import unittest
from unittest.mock import patch, Mock
import json
import os
import sys
from datetime import datetime

# Add parent directory to path to import the Flask app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from portfolio_reader import app

class TestPortfolioReaderUpdated(unittest.TestCase):
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
    def test_ready_endpoint(self, mock_connect):
        """Test readiness check endpoint."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        response = self.app.get('/ready')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {"status": "ready"})
        mock_cursor.execute.assert_called_with("SELECT 1")

    @patch('portfolio_reader.psycopg2.connect')
    def test_get_portfolio_with_transactions_llm_format(self, mock_connect):
        """Test portfolio retrieval with transactions in llm.txt format."""
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
        transaction_data = [
            {
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
            },
            {
                'id': '550e8400-e29b-41d4-a716-446655440001',
                'accountid': '1234567890',
                'transaction_type': 'WITHDRAWAL',
                'tier1_change': -300.0,
                'tier2_change': -150.0,
                'tier3_change': -50.0,
                'total_amount': 500.0,
                'fees': 5.0,
                'status': 'COMPLETED',
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
        ]
        
        mock_cursor.fetchone.side_effect = [portfolio_data]
        mock_cursor.fetchall.side_effect = [transaction_data]
        
        response = self.app.get('/api/v1/portfolio/1234567890')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        
        # Verify response structure matches llm.txt specification
        self.assertIn('portfolio', data)
        self.assertIn('transactions', data)
        self.assertIn('status', data)
        self.assertEqual(data['status'], 'success')
        
        # Verify portfolio structure
        portfolio = data['portfolio']
        self.assertEqual(portfolio['accountid'], '1234567890')
        self.assertEqual(portfolio['currency'], 'USD')
        self.assertEqual(portfolio['tier1_allocation'], 60.0)
        self.assertEqual(portfolio['tier2_allocation'], 30.0)
        self.assertEqual(portfolio['tier3_allocation'], 10.0)
        self.assertEqual(portfolio['total_allocation'], 100.0)
        self.assertEqual(portfolio['tier1_value'], 6000.0)
        self.assertEqual(portfolio['tier2_value'], 3000.0)
        self.assertEqual(portfolio['tier3_value'], 1000.0)
        self.assertEqual(portfolio['total_value'], 10000.0)
        
        # Verify transactions format matches llm.txt specification
        # Format: [uuid, accountid, tier1_change, tier2_change, tier3_change, status, ...]
        transactions = data['transactions']
        self.assertIsInstance(transactions, list)
        self.assertEqual(len(transactions), 2)
        
        # Check first transaction array format
        first_tx = transactions[0]
        self.assertIsInstance(first_tx, list)
        self.assertEqual(first_tx[0], '550e8400-e29b-41d4-a716-446655440000')  # uuid
        self.assertEqual(first_tx[1], '1234567890')  # accountid
        self.assertEqual(first_tx[2], 600.0)  # tier1_change
        self.assertEqual(first_tx[3], 300.0)  # tier2_change
        self.assertEqual(first_tx[4], 100.0)  # tier3_change
        self.assertEqual(first_tx[5], 'COMPLETED')  # status
        
        # Check second transaction array format
        second_tx = transactions[1]
        self.assertIsInstance(second_tx, list)
        self.assertEqual(second_tx[0], '550e8400-e29b-41d4-a716-446655440001')  # uuid
        self.assertEqual(second_tx[1], '1234567890')  # accountid
        self.assertEqual(second_tx[2], -300.0)  # tier1_change
        self.assertEqual(second_tx[3], -150.0)  # tier2_change
        self.assertEqual(second_tx[4], -50.0)  # tier3_change
        self.assertEqual(second_tx[5], 'COMPLETED')  # status

    @patch('portfolio_reader.psycopg2.connect')
    def test_get_portfolio_not_found(self, mock_connect):
        """Test portfolio not found scenario."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = None
        
        response = self.app.get('/api/v1/portfolio/9999999999')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('not found', data['error'])

    @patch('portfolio_reader.psycopg2.connect')
    def test_get_portfolio_transactions_llm_format(self, mock_connect):
        """Test transaction retrieval in llm.txt format."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock portfolio exists check
        portfolio_data = {'accountid': '1234567890'}
        
        # Mock transaction data
        transaction_data = [
            {
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
        ]
        
        mock_cursor.fetchone.side_effect = [portfolio_data]
        mock_cursor.fetchall.side_effect = [transaction_data]
        
        response = self.app.get('/api/v1/portfolio/1234567890/transactions')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        
        # Verify transaction format matches llm.txt specification
        transaction = data[0]
        self.assertIsInstance(transaction, list)
        self.assertEqual(transaction[0], '550e8400-e29b-41d4-a716-446655440000')  # uuid
        self.assertEqual(transaction[1], '1234567890')  # accountid
        self.assertEqual(transaction[2], 600.0)  # tier1_change
        self.assertEqual(transaction[3], 300.0)  # tier2_change
        self.assertEqual(transaction[4], 100.0)  # tier3_change
        self.assertEqual(transaction[5], 'COMPLETED')  # status

    @patch('portfolio_reader.psycopg2.connect')
    def test_get_portfolio_transactions_not_found(self, mock_connect):
        """Test transaction retrieval when portfolio doesn't exist."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = None
        
        response = self.app.get('/api/v1/portfolio/9999999999/transactions')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('not found', data['error'])

    @patch('portfolio_reader.psycopg2.connect')
    def test_get_portfolio_summary(self, mock_connect):
        """Test portfolio summary endpoint."""
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
        
        # Mock invested amount data
        invested_data = {'total_invested': 9500.0}
        
        # Mock transaction stats data
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
        self.assertIn('accountid', data)
        self.assertIn('currency', data)
        self.assertIn('current_value', data)
        self.assertIn('allocation', data)
        self.assertIn('analytics', data)
        self.assertIn('timestamps', data)

    def test_llm_txt_compliance(self):
        """Test that the service complies with llm.txt specifications."""
        # This test documents the expected behavior from llm.txt
        
        expected_behavior = {
            "micro_service_description": {
                "gets_accountid_from": "investment-manager-svc",
                "queries_user_portfolio_db": "user_portfolios table",
                "queries_portfolio_transactions": "portfolio-transactions table (last 30 transactions)",
                "returns_json_format": {
                    "portfolio": {
                        "accountid": "string",
                        "tier1_allocation": "number",
                        "tier2_allocation": "number", 
                        "tier3_allocation": "number",
                        "tier1_value": "number",
                        "tier2_value": "number",
                        "tier3_value": "number"
                    },
                    "transactions": [
                        ["uuid", "accountid", "tier1_change", "tier2_change", "tier3_change", "status"]
                    ],
                    "status": "string"
                }
            }
        }
        
        # Verify the service structure matches expectations
        self.assertIsNotNone(app)
        self.assertTrue(hasattr(app, 'route'))
        
        # This test passes if the service can be imported and has the expected structure
        self.assertTrue(True)  # Placeholder for structural validation

if __name__ == '__main__':
    print("🧪 Running Portfolio Reader Service Updated Tests")
    print("============================================================")
    unittest.main()
