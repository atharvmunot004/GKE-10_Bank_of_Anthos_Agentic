import unittest
from unittest.mock import patch, Mock
import json
import os
import sys
from datetime import datetime

# Add parent directory to path to import the Flask app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from market_reader_svc import app

class TestMarketReaderSvc(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        os.environ['ASSETS_DB_URI'] = 'postgresql://user:password@host:port/database'
        os.environ['REQUEST_TIMEOUT'] = '1'

    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {"status": "healthy"})

    @patch('market_reader_svc.get_db_connection')
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

    def test_market_data_invalid_type(self):
        """Test market data request with invalid type."""
        response = self.app.post('/api/v1/market-data',
                                 json={"type": "INVALID"})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'failed')
        self.assertIn('Invalid asset type', data['error'])

    def test_market_data_missing_type(self):
        """Test market data request without type."""
        response = self.app.post('/api/v1/market-data',
                                 json={})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'failed')

    @patch('market_reader_svc.update_asset_price')
    @patch('market_reader_svc.get_assets_by_tier')
    def test_market_data_crypto_success(self, mock_get_assets, mock_update_price):
        """Test successful crypto market data request."""
        # Mock assets data
        mock_assets = [
            {
                'asset_id': 1,
                'tier_number': 1,
                'asset_name': 'BTC',
                'amount': 1000.0,
                'price_per_unit': 50000.0,
                'last_updated': datetime.now()
            },
            {
                'asset_id': 2,
                'tier_number': 1,
                'asset_name': 'ETH',
                'amount': 5000.0,
                'price_per_unit': 3000.0,
                'last_updated': datetime.now()
            }
        ]
        mock_get_assets.return_value = mock_assets
        mock_update_price.return_value = True
        
        response = self.app.post('/api/v1/market-data',
                                 json={"type": "CRYPTO"})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['asset_type'], 'CRYPTO')
        self.assertEqual(len(data['assets']), 2)
        self.assertIn('analytics', data)

    @patch('market_reader_svc.update_asset_price')
    @patch('market_reader_svc.get_assets_by_tier')
    def test_market_data_etf_success(self, mock_get_assets, mock_update_price):
        """Test successful ETF market data request."""
        mock_assets = [
            {
                'asset_id': 3,
                'tier_number': 2,
                'asset_name': 'SPY',
                'amount': 10000.0,
                'price_per_unit': 400.0,
                'last_updated': datetime.now()
            }
        ]
        mock_get_assets.return_value = mock_assets
        mock_update_price.return_value = True
        
        response = self.app.post('/api/v1/market-data',
                                 json={"type": "ETF"})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['asset_type'], 'ETF')

    @patch('market_reader_svc.get_assets_by_tier')
    def test_market_data_no_assets(self, mock_get_assets):
        """Test market data request when no assets found."""
        mock_get_assets.return_value = []
        
        response = self.app.post('/api/v1/market-data',
                                 json={"type": "CRYPTO"})
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'failed')
        self.assertIn('No assets found', data['error'])

    @patch('market_reader_svc.get_assets_by_tier')
    def test_market_summary_success(self, mock_get_assets):
        """Test successful market summary request."""
        mock_assets = [
            {
                'asset_id': 1,
                'tier_number': 1,
                'asset_name': 'BTC',
                'amount': 1000.0,
                'price_per_unit': 50000.0,
                'last_updated': datetime.now()
            },
            {
                'asset_id': 2,
                'tier_number': 2,
                'asset_name': 'SPY',
                'amount': 10000.0,
                'price_per_unit': 400.0,
                'last_updated': datetime.now()
            }
        ]
        
        # Mock different calls for different tiers
        def side_effect(tier):
            if tier == 1:
                return [mock_assets[0]]
            elif tier == 2:
                return [mock_assets[1]]
            else:
                return []
        
        mock_get_assets.side_effect = side_effect
        
        response = self.app.get('/api/v1/market-summary')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('total_assets', data)
        self.assertIn('total_market_value', data)
        self.assertIn('tier_breakdown', data)

    @patch('market_reader_svc.get_assets_by_tier')
    def test_market_summary_no_assets(self, mock_get_assets):
        """Test market summary when no assets found."""
        mock_get_assets.return_value = []
        
        response = self.app.get('/api/v1/market-summary')
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'failed')

    def test_price_simulation_functions(self):
        """Test price simulation functions."""
        from market_reader_svc import (
            simulate_crypto_price, simulate_etf_price, 
            simulate_mutual_fund_price, simulate_equity_price
        )
        
        base_price = 100.0
        
        # Test crypto simulation (should have higher volatility)
        crypto_price = simulate_crypto_price(base_price)
        self.assertIsInstance(crypto_price, float)
        self.assertGreater(crypto_price, 0)
        
        # Test ETF simulation
        etf_price = simulate_etf_price(base_price)
        self.assertIsInstance(etf_price, float)
        self.assertGreater(etf_price, 0)
        
        # Test mutual fund simulation
        mf_price = simulate_mutual_fund_price(base_price)
        self.assertIsInstance(mf_price, float)
        self.assertGreater(mf_price, 0)
        
        # Test equity simulation
        equity_price = simulate_equity_price(base_price)
        self.assertIsInstance(equity_price, float)
        self.assertGreater(equity_price, 0)

    def test_analytics_generation(self):
        """Test market analytics generation."""
        from market_reader_svc import generate_market_analytics
        
        mock_assets = [
            {
                'asset_name': 'BTC',
                'amount': 1000.0,
                'price_per_unit': 50000.0
            },
            {
                'asset_name': 'ETH',
                'amount': 5000.0,
                'price_per_unit': 3000.0
            }
        ]
        
        analytics = generate_market_analytics(mock_assets, 'CRYPTO')
        
        self.assertEqual(analytics['market_type'], 'CRYPTO')
        self.assertEqual(analytics['total_assets'], 2)
        self.assertIn('price_summary', analytics)
        self.assertIn('volatility_analysis', analytics)
        self.assertIn('portfolio_recommendations', analytics)

    def test_valid_asset_types(self):
        """Test all valid asset types."""
        valid_types = ['CRYPTO', 'ETF', 'MUTUAL-FUND', 'EQUITY']
        
        for asset_type in valid_types:
            response = self.app.post('/api/v1/market-data',
                                     json={"type": asset_type})
            # Should not return 400 for invalid type
            self.assertNotEqual(response.status_code, 400)

if __name__ == '__main__':
    print("🧪 Running Market Reader Service Unit Tests")
    print("============================================================")
    unittest.main()
