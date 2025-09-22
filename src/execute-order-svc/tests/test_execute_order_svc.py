import unittest
from unittest.mock import patch, Mock
import json
import os
import sys
from datetime import datetime

# Add parent directory to path to import the Flask app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from execute_order_svc import app

class TestExecuteOrderSvc(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        os.environ['ASSETS_DB_URI'] = 'postgresql://user:password@host:port/database'
        os.environ['REQUEST_TIMEOUT'] = '1'
        os.environ['TIER1'] = '1000000.0'
        os.environ['TIER2'] = '2000000.0'
        os.environ['TIER3'] = '500000.0'

    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {"status": "healthy"})

    @patch('execute_order_svc.get_db_connection')
    def test_ready_endpoint(self, mock_db_connect):
        """Test readiness check endpoint."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        response = self.app.get('/ready')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {"status": "ready"})
        mock_cursor.execute.assert_called_with("SELECT 1")

    def test_execute_order_missing_fields(self):
        """Test execute order with missing required fields."""
        response = self.app.post('/api/v1/execute-order',
                                 json={"asset_id": "BTC001"})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'failed')
        self.assertIn('missing_field', data['error'])

    def test_execute_order_invalid_tier(self):
        """Test execute order with invalid tier number."""
        order_data = {
            "asset_id": "BTC001",
            "asset_type": "CRYPTO",
            "tier_number": 4,
            "asset_name": "Bitcoin",
            "amount_trade": 100.0,
            "price": 50000.0,
            "purpose": "BUY"
        }
        
        response = self.app.post('/api/v1/execute-order', json=order_data)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'failed')
        self.assertIn('invalid_tier', data['error'])

    def test_execute_order_invalid_purpose(self):
        """Test execute order with invalid purpose."""
        order_data = {
            "asset_id": "BTC001",
            "asset_type": "CRYPTO",
            "tier_number": 1,
            "asset_name": "Bitcoin",
            "amount_trade": 100.0,
            "price": 50000.0,
            "purpose": "INVALID"
        }
        
        response = self.app.post('/api/v1/execute-order', json=order_data)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'failed')
        self.assertIn('invalid_purpose', data['error'])

    def test_execute_order_invalid_amount_or_price(self):
        """Test execute order with invalid amount or price."""
        order_data = {
            "asset_id": "BTC001",
            "asset_type": "CRYPTO",
            "tier_number": 1,
            "asset_name": "Bitcoin",
            "amount_trade": -100.0,
            "price": 50000.0,
            "purpose": "BUY"
        }
        
        response = self.app.post('/api/v1/execute-order', json=order_data)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'failed')
        self.assertIn('invalid_amount_or_price', data['error'])

    @patch('execute_order_svc.update_tier_market_values')
    @patch('execute_order_svc.process_buy_order')
    def test_execute_order_buy_success(self, mock_process_buy, mock_update_tier):
        """Test successful BUY order execution."""
        mock_update_tier.return_value = True
        mock_process_buy.return_value = {
            "status": "executed",
            "order_id": "test-order-id",
            "asset_id": "BTC001",
            "asset_name": "Bitcoin",
            "amount_traded": 100.0,
            "price_executed": 50000.0,
            "total_value": 5000000.0,
            "new_amount": 100.0,
            "execution_probability": 0.85,
            "message": "BUY order executed successfully"
        }
        
        order_data = {
            "asset_id": "BTC001",
            "asset_type": "CRYPTO",
            "tier_number": 1,
            "asset_name": "Bitcoin",
            "amount_trade": 100.0,
            "price": 50000.0,
            "purpose": "BUY"
        }
        
        response = self.app.post('/api/v1/execute-order', json=order_data)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'executed')
        self.assertIn('order_id', data)
        mock_process_buy.assert_called_once()

    @patch('execute_order_svc.update_tier_market_values')
    @patch('execute_order_svc.process_sell_order')
    def test_execute_order_sell_success(self, mock_process_sell, mock_update_tier):
        """Test successful SELL order execution."""
        mock_update_tier.return_value = True
        mock_process_sell.return_value = {
            "status": "executed",
            "order_id": "test-order-id",
            "asset_id": "BTC001",
            "asset_name": "Bitcoin",
            "amount_traded": 50.0,
            "price_executed": 50000.0,
            "total_value": 2500000.0,
            "new_amount": 50.0,
            "execution_probability": 0.90,
            "message": "SELL order executed successfully"
        }
        
        order_data = {
            "asset_id": "BTC001",
            "asset_type": "CRYPTO",
            "tier_number": 1,
            "asset_name": "Bitcoin",
            "amount_trade": 50.0,
            "price": 50000.0,
            "purpose": "SELL"
        }
        
        response = self.app.post('/api/v1/execute-order', json=order_data)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'executed')
        self.assertIn('order_id', data)
        mock_process_sell.assert_called_once()

    @patch('execute_order_svc.update_tier_market_values')
    def test_tier_status_success(self, mock_update_tier):
        """Test successful tier status retrieval."""
        mock_update_tier.return_value = True
        
        response = self.app.get('/api/v1/tier-status')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('tier_pools', data)
        self.assertIn('tier_market_values', data)

    def test_calculate_order_probability(self):
        """Test order probability calculation."""
        from execute_order_svc import calculate_order_probability
        
        # Test with same price and amount (should be high probability)
        probability = calculate_order_probability(100.0, 10.0, 100.0, 10.0)
        self.assertGreater(probability, 0.5)
        self.assertLessEqual(probability, 1.0)
        
        # Test with different price (should be lower probability)
        probability2 = calculate_order_probability(100.0, 10.0, 200.0, 10.0)
        self.assertLess(probability2, probability)

    def test_get_tier_pool(self):
        """Test tier pool retrieval."""
        from execute_order_svc import get_tier_pool
        
        self.assertEqual(get_tier_pool(1), 1000000.0)
        self.assertEqual(get_tier_pool(2), 2000000.0)
        self.assertEqual(get_tier_pool(3), 500000.0)
        self.assertEqual(get_tier_pool(4), 0.0)

    @patch('execute_order_svc.psycopg2.connect')
    def test_get_asset_by_id_success(self, mock_connect):
        """Test successful asset retrieval by ID."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        mock_asset = {
            'asset_id': 'BTC001',
            'tier_number': 1,
            'asset_name': 'Bitcoin',
            'amount': 100.0,
            'price_per_unit': 50000.0,
            'last_updated': datetime.now()
        }
        mock_cursor.fetchone.return_value = mock_asset
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        from execute_order_svc import get_asset_by_id
        result = get_asset_by_id('BTC001')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['asset_id'], 'BTC001')

    @patch('execute_order_svc.psycopg2.connect')
    def test_get_asset_by_id_not_found(self, mock_connect):
        """Test asset retrieval when asset not found."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        mock_cursor.fetchone.return_value = None
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        from execute_order_svc import get_asset_by_id
        result = get_asset_by_id('NONEXISTENT')
        
        self.assertIsNone(result)

if __name__ == '__main__':
    print("🧪 Running Execute Order Service Unit Tests")
    print("============================================================")
    unittest.main()
