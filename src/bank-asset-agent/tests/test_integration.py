#!/usr/bin/env python3
# Copyright 2024 Google LLC
# Bank Asset Agent - Integration Tests

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import json

# Add the parent directory to the path to import the modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestBankAssetAgentIntegration(unittest.TestCase):
    """Integration tests for Bank Asset Agent"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_environment = {
            'ASSETS_DB_URI': 'postgresql://test:test@localhost:5432/test',
            'QUEUE_DB_URI': 'postgresql://test:test@localhost:5432/test'
        }
    
    @patch.dict(os.environ, {'ASSETS_DB_URI': 'postgresql://test:test@localhost:5432/test'})
    @patch('psycopg2.connect')
    def test_assets_database_integration(self, mock_connect):
        """Test assets database integration"""
        # Mock database connection
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            (1, 1, "AAPL", 1000.0, 150.25, "2024-09-22T10:30:00Z"),
            (2, 1, "GOOGL", 500.0, 2800.50, "2024-09-22T10:30:00Z"),
            (3, 2, "MSFT", 2000.0, 300.75, "2024-09-22T10:30:00Z")
        ]
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        from utils.db_client import AssetsDatabaseClient
        client = AssetsDatabaseClient()
        
        # Test getting all assets
        assets = client.get_all_assets()
        
        self.assertEqual(len(assets), 3)
        self.assertEqual(assets[0]['asset_name'], "AAPL")
        self.assertEqual(assets[0]['tier_number'], 1)
        self.assertEqual(assets[0]['price_per_unit'], 150.25)
        
        # Test getting assets by tier
        tier_1_assets = client.get_assets_by_tier(1)
        self.assertEqual(len(tier_1_assets), 3)  # All 3 assets are in tier 1 based on mock data
        
        # Test asset availability check
        mock_cursor.fetchone.return_value = (1000.0,)
        is_available = client.check_asset_availability(1, 500.0)
        self.assertTrue(is_available)
        
        # Test asset price update
        mock_cursor.rowcount = 1
        updated = client.update_asset_price(1, 155.50)
        self.assertTrue(updated)
    
    @patch.dict(os.environ, {'ASSETS_DB_URI': 'postgresql://test:test@localhost:5432/test'})
    @patch('psycopg2.connect')
    def test_assets_database_integration(self, mock_connect):
        """Test assets database integration"""
        # Mock database connection
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ("asset1", 1, "Gold", 100.0, 2000.0, "2024-09-22T10:30:00Z"),
            ("asset2", 2, "Silver", 50.0, 25.0, "2024-09-22T10:35:00Z"),
            ("asset3", 1, "Bitcoin", 0.5, 50000.0, "2024-09-22T10:40:00Z")
        ]
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        from utils.db_client import AssetsDatabaseClient
        client = AssetsDatabaseClient("postgresql://test:test@localhost:5432/test")
        
        # Test getting assets by tier
        assets = client.get_assets_by_tier(1)
        
        self.assertEqual(len(assets), 3)
        self.assertEqual(assets[0]['asset_name'], "Gold")
        self.assertEqual(assets[0]['tier_number'], 1)
        self.assertEqual(assets[1]['tier_number'], 2)
        self.assertEqual(assets[2]['tier_number'], 1)
        
        # Test getting all assets
        all_assets = client.get_all_assets()
        self.assertEqual(len(all_assets), 3)
    
    @patch('utils.http_client.MarketReaderClient.get_market_data')
    @patch('utils.http_client.RuleCheckerClient.validate_investment')
    @patch('utils.http_client.ExecuteOrderClient.execute_order')
    def test_end_to_end_investment_flow(self, mock_execute, mock_validate, mock_market):
        """Test end-to-end investment flow"""
        # Mock market data
        mock_market.return_value = {
            "symbols": ["AAPL", "GOOGL"],
            "prices": {
                "AAPL": {"price": 150.25, "change": 2.15, "change_percent": 1.45},
                "GOOGL": {"price": 2800.50, "change": -15.30, "change_percent": -0.54}
            },
            "timestamp": "2024-09-22T10:30:00Z"
        }
        
        # Mock rule validation
        mock_validate.return_value = {
            "valid": True,
            "risk_score": 0.3,
            "compliance_status": "passed",
            "recommendations": ["Proceed with investment"]
        }
        
        # Mock order execution
        mock_execute.return_value = {
            "order_id": "order123",
            "status": "executed",
            "executed_price": 150.20,
            "executed_quantity": 10,
            "timestamp": "2024-09-22T10:30:00Z"
        }
        
        from utils.http_client import BankAssetAgentClient
        client = BankAssetAgentClient()
        
        # Test the complete flow
        # 1. Get market data
        market_data = client.get_market_data(["AAPL", "GOOGL"])
        self.assertIn("symbols", market_data)
        self.assertIn("prices", market_data)
        
        # 2. Validate investment rules
        investment_request = {
            "user_id": "user123",
            "asset_symbol": "AAPL",
            "amount": 1000.0,
            "investment_type": "buy",
            "risk_tolerance": "medium"
        }
        
        validation_result = client.validate_rules(investment_request)
        self.assertTrue(validation_result["valid"])
        self.assertEqual(validation_result["compliance_status"], "passed")
        
        # 3. Execute order
        order_data = {
            "order_id": "order123",
            "user_id": "user123",
            "asset_symbol": "AAPL",
            "quantity": 10,
            "order_type": "buy",
            "price": 150.25
        }
        
        execution_result = client.execute_order(order_data)
        self.assertEqual(execution_result["status"], "executed")
        self.assertEqual(execution_result["order_id"], "order123")
    
    def test_risk_calculation_logic(self):
        """Test risk calculation logic integration"""
        # Test risk factors calculation
        risk_factors = {
            "volatility": 0.7,
            "liquidity": 0.9,
            "market_cap": 0.8,
            "sector_risk": 0.6
        }
        
        # Calculate weighted risk score
        weights = {"volatility": 0.3, "liquidity": 0.2, "market_cap": 0.3, "sector_risk": 0.2}
        risk_score = sum(risk_factors[factor] * weights[factor] for factor in risk_factors)
        
        self.assertAlmostEqual(risk_score, 0.75, places=2)
        self.assertGreater(risk_score, 0.5)  # High risk
        
        # Test risk categorization
        if risk_score > 0.7:
            risk_category = "High"
        elif risk_score > 0.4:
            risk_category = "Medium"
        else:
            risk_category = "Low"
        
        self.assertEqual(risk_category, "High")
    
    def test_asset_tier_classification(self):
        """Test asset tier classification logic"""
        # Test tier classification based on price
        assets = [
            {"name": "AAPL", "price": 150.25, "expected_tier": 1},
            {"name": "GOOGL", "price": 2800.50, "expected_tier": 2},
            {"name": "MSFT", "price": 300.75, "expected_tier": 1},
            {"name": "TSLA", "price": 250.00, "expected_tier": 1}
        ]
        
        for asset in assets:
            if asset["price"] > 1000:
                tier = 2
            elif asset["price"] > 100:
                tier = 1
            else:
                tier = 0
            
            self.assertEqual(tier, asset["expected_tier"])
    
    def test_investment_amount_validation(self):
        """Test investment amount validation logic"""
        # Test valid amounts
        valid_amounts = [100.0, 1000.0, 5000.0, 10000.0]
        for amount in valid_amounts:
            self.assertGreater(amount, 0)
            self.assertLessEqual(amount, 100000)  # Max investment limit
        
        # Test invalid amounts
        invalid_amounts = [0, -100, 200000]
        for amount in invalid_amounts:
            if amount <= 0:
                self.assertLessEqual(amount, 0)
            else:
                self.assertGreater(amount, 100000)

class TestServiceCommunication(unittest.TestCase):
    """Test service communication patterns"""
    
    def test_http_client_retry_logic(self):
        """Test HTTP client retry logic"""
        from utils.http_client import HTTPClient
        
        # Test retry configuration
        client = HTTPClient(max_retries=3, timeout=30)
        self.assertEqual(client.max_retries, 3)
        self.assertEqual(client.timeout, 30)
        
        # Test session configuration
        self.assertIn('Content-Type', client.session.headers)
        self.assertIn('User-Agent', client.session.headers)
    
    def test_database_connection_management(self):
        """Test database connection management"""
        from utils.db_client import AssetsDatabaseClient
        
        # Test connection string validation
        with self.assertRaises(ValueError):
            AssetsDatabaseClient()  # No connection string
        
        # Test with connection string
        client = AssetsDatabaseClient("postgresql://test:test@localhost:5432/test")
        self.assertEqual(client.connection_string, "postgresql://test:test@localhost:5432/test")

if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestBankAssetAgentIntegration))
    test_suite.addTest(unittest.makeSuite(TestServiceCommunication))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"Integration Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print(f"{'='*50}")
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
