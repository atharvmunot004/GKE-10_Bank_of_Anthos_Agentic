import unittest
from unittest.mock import patch, Mock
import json
import os
import sys
from datetime import datetime

# Add parent directory to path to import the Flask app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from market_reader_svc import app

class TestMarketReaderIntegration(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        os.environ['ASSETS_DB_URI'] = 'postgresql://user:password@host:port/database'
        os.environ['REQUEST_TIMEOUT'] = '1'

    @patch('market_reader_svc.psycopg2.connect')
    @patch('market_reader_svc.get_real_market_data')
    @patch('market_reader_svc.update_asset_price')
    def test_full_crypto_market_data_flow(self, mock_update_price, mock_real_data, mock_connect):
        """Test complete crypto market data flow."""
        # Mock database connection and cursor
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
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
        
        # Mock cursor behavior
        mock_cursor.fetchall.return_value = mock_assets
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        # Mock no real market data (use simulation)
        mock_real_data.return_value = None
        mock_update_price.return_value = True
        
        response = self.app.post('/api/v1/market-data',
                                 json={"type": "CRYPTO"})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Verify response structure
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['asset_type'], 'CRYPTO')
        self.assertEqual(len(data['assets']), 2)
        
        # Verify each asset has required fields
        for asset in data['assets']:
            self.assertIn('asset_id', asset)
            self.assertIn('asset_name', asset)
            self.assertIn('tier_number', asset)
            self.assertIn('amount', asset)
            self.assertIn('price_per_unit', asset)
            self.assertIn('market_value', asset)
            self.assertIn('price_change_percent', asset)
            self.assertIn('last_updated', asset)
        
        # Verify analytics structure
        analytics = data['analytics']
        self.assertIn('market_type', analytics)
        self.assertIn('timestamp', analytics)
        self.assertIn('total_assets', analytics)
        self.assertIn('price_summary', analytics)
        self.assertIn('volatility_analysis', analytics)
        self.assertIn('portfolio_recommendations', analytics)
        
        # Verify database interactions
        self.assertTrue(mock_cursor.execute.called)
        self.assertTrue(mock_update_price.called)

    @patch('market_reader_svc.psycopg2.connect')
    def test_etf_with_real_market_data(self, mock_connect):
        """Test ETF processing with real market data."""
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock ETF asset
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
        
        mock_cursor.fetchall.return_value = mock_assets
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        # Mock real market data
        with patch('market_reader_svc.get_real_market_data') as mock_real_data:
            mock_real_data.return_value = 420.0  # Real market price
            
            with patch('market_reader_svc.update_asset_price') as mock_update:
                mock_update.return_value = True
                
                response = self.app.post('/api/v1/market-data',
                                         json={"type": "ETF"})
                
                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                
                # Verify real market data was used
                self.assertEqual(data['assets'][0]['price_per_unit'], 420.0)
                mock_real_data.assert_called_with('SPY', 'ETF')

    @patch('market_reader_svc.psycopg2.connect')
    def test_market_summary_integration(self, mock_connect):
        """Test market summary with multiple tiers."""
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock different assets for different tiers
        def mock_fetchall(query, params):
            tier = params[0] if params else None
            if tier == 1:
                return [
                    {
                        'asset_id': 1,
                        'tier_number': 1,
                        'asset_name': 'BTC',
                        'amount': 1000.0,
                        'price_per_unit': 50000.0,
                        'last_updated': datetime.now()
                    }
                ]
            elif tier == 2:
                return [
                    {
                        'asset_id': 2,
                        'tier_number': 2,
                        'asset_name': 'SPY',
                        'amount': 10000.0,
                        'price_per_unit': 400.0,
                        'last_updated': datetime.now()
                    },
                    {
                        'asset_id': 3,
                        'tier_number': 2,
                        'asset_name': 'QQQ',
                        'amount': 5000.0,
                        'price_per_unit': 350.0,
                        'last_updated': datetime.now()
                    }
                ]
            else:
                return []
        
        mock_cursor.fetchall.side_effect = mock_fetchall
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        response = self.app.get('/api/v1/market-summary')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Verify summary structure
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['total_assets'], 3)
        self.assertIn('total_market_value', data)
        self.assertIn('tier_breakdown', data)
        
        # Verify tier breakdown
        tier_breakdown = data['tier_breakdown']
        self.assertIn('tier_1', tier_breakdown)
        self.assertIn('tier_2', tier_breakdown)
        self.assertNotIn('tier_3', tier_breakdown)  # No assets in tier 3
        
        # Verify tier 1 calculations
        tier_1 = tier_breakdown['tier_1']
        self.assertEqual(tier_1['asset_count'], 1)
        self.assertEqual(tier_1['total_value'], 50000000.0)  # 1000 * 50000
        
        # Verify tier 2 calculations
        tier_2 = tier_breakdown['tier_2']
        self.assertEqual(tier_2['asset_count'], 2)
        self.assertEqual(tier_2['total_value'], 5750000.0)  # (10000 * 400) + (5000 * 350)

    def test_error_handling_database_connection_failure(self):
        """Test error handling when database connection fails."""
        with patch('market_reader_svc.psycopg2.connect') as mock_connect:
            mock_connect.side_effect = Exception("Database connection failed")
            
            response = self.app.post('/api/v1/market-data',
                                     json={"type": "CRYPTO"})
            
            self.assertEqual(response.status_code, 500)
            data = json.loads(response.data)
            self.assertEqual(data['status'], 'failed')
            self.assertIn('error', data)

    def test_error_handling_invalid_json(self):
        """Test error handling for invalid JSON."""
        response = self.app.post('/api/v1/market-data',
                                 data="invalid json",
                                 content_type='application/json')
        
        self.assertEqual(response.status_code, 400)

    def test_analytics_recommendations_for_different_asset_types(self):
        """Test analytics recommendations for different asset types."""
        from market_reader_svc import generate_market_analytics
        
        # Test crypto analytics
        crypto_assets = [
            {
                'asset_name': 'BTC',
                'amount': 1000.0,
                'price_per_unit': 50000.0
            }
        ]
        
        crypto_analytics = generate_market_analytics(crypto_assets, 'CRYPTO')
        self.assertEqual(crypto_analytics['portfolio_recommendations']['risk_level'], 'high')
        self.assertEqual(len(crypto_analytics['volatility_analysis']['high_volatility_assets']), 1)
        
        # Test ETF analytics
        etf_assets = [
            {
                'asset_name': 'SPY',
                'amount': 10000.0,
                'price_per_unit': 400.0
            }
        ]
        
        etf_analytics = generate_market_analytics(etf_assets, 'ETF')
        self.assertEqual(etf_analytics['portfolio_recommendations']['risk_level'], 'medium')
        self.assertGreater(len(etf_analytics['volatility_analysis']['stable_assets']), 0)
        
        # Test mutual fund analytics
        mf_assets = [
            {
                'asset_name': 'VTSAX',
                'amount': 5000.0,
                'price_per_unit': 100.0
            }
        ]
        
        mf_analytics = generate_market_analytics(mf_assets, 'MUTUAL-FUND')
        self.assertEqual(mf_analytics['portfolio_recommendations']['risk_level'], 'low')
        self.assertEqual(len(mf_analytics['volatility_analysis']['recommended_for_long_term']), 1)

if __name__ == '__main__':
    print("🔗 Running Market Reader Service Integration Tests")
    print("============================================================")
    unittest.main()
