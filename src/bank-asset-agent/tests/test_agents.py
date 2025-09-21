#!/usr/bin/env python3
# Copyright 2024 Google LLC
# Bank Asset Agent - Unit Tests for AI Agents

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import json

# Add the parent directory to the path to import the agent modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestMarketAnalyzer(unittest.TestCase):
    """Test cases for Market Analyzer Agent"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_market_data = {
            "symbols": ["AAPL", "GOOGL", "MSFT"],
            "prices": {
                "AAPL": {"price": 150.25, "change": 2.15, "change_percent": 1.45},
                "GOOGL": {"price": 2800.50, "change": -15.30, "change_percent": -0.54},
                "MSFT": {"price": 300.75, "change": 5.20, "change_percent": 1.76}
            },
            "timestamp": "2024-09-22T10:30:00Z"
        }
    
    @patch('utils.http_client.MarketReaderClient.get_market_data')
    def test_get_market_data_success(self, mock_get_market_data):
        """Test successful market data retrieval"""
        # Mock the response
        mock_get_market_data.return_value = self.mock_market_data
        
        # Import and test the function
        from utils.http_client import BankAssetAgentClient
        client = BankAssetAgentClient()
        
        result = client.get_market_data(["AAPL", "GOOGL", "MSFT"])
        
        self.assertEqual(result, self.mock_market_data)
        mock_get_market_data.assert_called_once_with(["AAPL", "GOOGL", "MSFT"], "1d")
    
    @patch('utils.http_client.MarketReaderClient.get_market_data')
    def test_get_market_data_failure(self, mock_get_market_data):
        """Test market data retrieval failure"""
        # Mock the response to raise an exception
        mock_get_market_data.side_effect = Exception("Connection error after 3 attempts")
        
        from utils.http_client import BankAssetAgentClient
        client = BankAssetAgentClient()
        
        with self.assertRaises(Exception):
            client.get_market_data(["AAPL"])
    
    def test_analyze_trends(self):
        """Test trend analysis functionality"""
        # Mock trend analysis
        trend_data = {
            "AAPL": {"trend": "bullish", "confidence": 0.85},
            "GOOGL": {"trend": "bearish", "confidence": 0.72},
            "MSFT": {"trend": "bullish", "confidence": 0.91}
        }
        
        # Test trend analysis logic
        bullish_stocks = [symbol for symbol, data in trend_data.items() if data["trend"] == "bullish"]
        bearish_stocks = [symbol for symbol, data in trend_data.items() if data["trend"] == "bearish"]
        
        self.assertEqual(len(bullish_stocks), 2)
        self.assertEqual(len(bearish_stocks), 1)
        self.assertIn("AAPL", bullish_stocks)
        self.assertIn("GOOGL", bearish_stocks)

class TestRuleValidator(unittest.TestCase):
    """Test cases for Rule Validator Agent"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.investment_request = {
            "user_id": "user123",
            "asset_symbol": "AAPL",
            "amount": 1000.0,
            "investment_type": "buy",
            "risk_tolerance": "medium"
        }
    
    @patch('utils.http_client.RuleCheckerClient.validate_investment')
    def test_validate_investment_rules_success(self, mock_validate):
        """Test successful rule validation"""
        # Mock the response
        mock_validate.return_value = {
            "valid": True,
            "risk_score": 0.3,
            "compliance_status": "passed",
            "recommendations": ["Proceed with investment"]
        }
        
        from utils.http_client import BankAssetAgentClient
        client = BankAssetAgentClient()
        
        result = client.validate_rules(self.investment_request)
        
        self.assertTrue(result["valid"])
        self.assertEqual(result["risk_score"], 0.3)
        mock_validate.assert_called_once_with(self.investment_request)
    
    @patch('utils.http_client.RuleCheckerClient.validate_investment')
    def test_validate_investment_rules_failure(self, mock_validate):
        """Test rule validation failure"""
        # Mock the response
        mock_validate.return_value = {
            "valid": False,
            "risk_score": 0.8,
            "compliance_status": "failed",
            "reasons": ["High risk investment", "Insufficient funds"]
        }
        
        from utils.http_client import BankAssetAgentClient
        client = BankAssetAgentClient()
        
        result = client.validate_rules(self.investment_request)
        
        self.assertFalse(result["valid"])
        self.assertEqual(result["risk_score"], 0.8)
        self.assertIn("High risk investment", result["reasons"])
    
    def test_risk_assessment(self):
        """Test risk assessment logic"""
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

class TestOrderExecutor(unittest.TestCase):
    """Test cases for Order Executor Agent"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.order_data = {
            "order_id": "order123",
            "user_id": "user123",
            "asset_symbol": "AAPL",
            "quantity": 10,
            "order_type": "buy",
            "price": 150.25
        }
    
    @patch('utils.http_client.ExecuteOrderClient.execute_order')
    def test_execute_buy_order_success(self, mock_execute):
        """Test successful buy order execution"""
        # Mock the response
        mock_execute.return_value = {
            "order_id": "order123",
            "status": "executed",
            "executed_price": 150.20,
            "executed_quantity": 10,
            "timestamp": "2024-09-22T10:30:00Z"
        }
        
        from utils.http_client import BankAssetAgentClient
        client = BankAssetAgentClient()
        
        result = client.execute_order(self.order_data)
        
        self.assertEqual(result["status"], "executed")
        self.assertEqual(result["order_id"], "order123")
        mock_execute.assert_called_once_with(self.order_data)
    
    @patch('utils.http_client.ExecuteOrderClient.execute_order')
    def test_execute_order_failure(self, mock_execute):
        """Test order execution failure"""
        # Mock the response
        mock_execute.return_value = {
            "order_id": "order123",
            "status": "failed",
            "error": "Insufficient funds",
            "timestamp": "2024-09-22T10:30:00Z"
        }
        
        from utils.http_client import BankAssetAgentClient
        client = BankAssetAgentClient()
        
        result = client.execute_order(self.order_data)
        
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"], "Insufficient funds")
    
    def test_order_validation(self):
        """Test order validation logic"""
        valid_order = {
            "asset_symbol": "AAPL",
            "quantity": 10,
            "order_type": "buy",
            "price": 150.25
        }
        
        # Validate order fields
        required_fields = ["asset_symbol", "quantity", "order_type", "price"]
        is_valid = all(field in valid_order for field in required_fields)
        
        self.assertTrue(is_valid)
        self.assertGreater(valid_order["quantity"], 0)
        self.assertGreater(valid_order["price"], 0)

class TestAssetDatabaseClient(unittest.TestCase):
    """Test cases for Asset Database Client"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_asset_data = {
            "asset_id": 1,
            "tier_number": 1,
            "asset_name": "AAPL",
            "amount": 1000.0,
            "price_per_unit": 150.25,
            "last_updated": "2024-09-22T10:30:00Z"
        }
    
    @patch('psycopg2.connect')
    def test_get_asset_info_success(self, mock_connect):
        """Test successful asset info retrieval"""
        # Mock database connection and cursor
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (1, 1, "AAPL", 1000.0, 150.25, "2024-09-22T10:30:00Z")
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        from utils.db_client import AssetsDatabaseClient
        client = AssetsDatabaseClient("postgresql://test:test@localhost:5432/test")
        
        result = client.get_asset_info(1)
        
        self.assertIsNotNone(result)
        mock_cursor.execute.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()
    
    @patch('psycopg2.connect')
    def test_update_asset_price_success(self, mock_connect):
        """Test successful asset price update"""
        # Mock database connection and cursor
        mock_cursor = Mock()
        mock_cursor.rowcount = 1  # Mock rowcount property
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        from utils.db_client import AssetsDatabaseClient
        client = AssetsDatabaseClient("postgresql://test:test@localhost:5432/test")
        
        result = client.update_asset_price(1, 155.50)
        
        self.assertTrue(result)
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()
    
    @patch('psycopg2.connect')
    def test_database_connection_failure(self, mock_connect):
        """Test database connection failure"""
        mock_connect.side_effect = Exception("Connection failed")
        
        from utils.db_client import AssetsDatabaseClient
        client = AssetsDatabaseClient("postgresql://test:test@localhost:5432/test")
        
        with self.assertRaises(Exception):
            client.get_asset_info(1)

if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestMarketAnalyzer))
    test_suite.addTest(unittest.makeSuite(TestRuleValidator))
    test_suite.addTest(unittest.makeSuite(TestOrderExecutor))
    test_suite.addTest(unittest.makeSuite(TestAssetDatabaseClient))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print(f"{'='*50}")
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
