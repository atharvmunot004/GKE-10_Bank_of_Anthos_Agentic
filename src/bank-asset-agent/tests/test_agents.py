#!/usr/bin/env python3
# Copyright 2024 Google LLC
# Bank Asset Agent - Unit Tests for AI Agents with Gemini Integration

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import json

# Add the parent directory to the path to import the agent modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up environment for AI testing
os.environ['GEMINI_API_KEY'] = 'test-api-key-for-testing'
os.environ['AI_ENABLED'] = 'true'
os.environ['AI_CONFIDENCE_THRESHOLD'] = '0.7'
os.environ['AI_FALLBACK_ENABLED'] = 'true'

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

class TestAIMarketAnalyzer(unittest.TestCase):
    """Test cases for AI Market Analyzer with Gemini Integration"""
    
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
        
        self.mock_ai_response = {
            "trend_analysis": "bullish",
            "confidence_score": 85,
            "reasoning": "Strong performance across tech stocks with positive momentum",
            "key_factors": ["Earnings growth", "Market sentiment", "Technical indicators"]
        }
    
    @patch('ai.gemini_client.GeminiAIClient.analyze_market_data')
    def test_ai_market_trend_analysis_success(self, mock_ai_analysis):
        """Test successful AI market trend analysis"""
        # Mock AI response
        mock_ai_analysis.return_value = self.mock_ai_response
        
        from tools.ai_market_analyzer import AIMarketAnalyzer
        analyzer = AIMarketAnalyzer()
        
        result = analyzer.analyze_market_trends(self.mock_market_data)
        
        self.assertEqual(result['trend_analysis'], "bullish")
        self.assertEqual(result['confidence_score'], 85)
        self.assertIn("reasoning", result)
        mock_ai_analysis.assert_called_once_with(self.mock_market_data)
    
    @patch('ai.gemini_client.GeminiAIClient.analyze_market_data')
    def test_ai_price_prediction_success(self, mock_ai_prediction):
        """Test successful AI price prediction"""
        mock_prediction_response = {
            "predictions": [
                {"symbol": "AAPL", "predicted_price": 155.30, "confidence": 0.8, "reasoning": "Strong fundamentals"},
                {"symbol": "GOOGL", "predicted_price": 2750.20, "confidence": 0.7, "reasoning": "Market volatility"}
            ],
            "overall_prediction_sentiment": "cautiously_optimistic"
        }
        mock_ai_prediction.return_value = mock_prediction_response
        
        from tools.ai_market_analyzer import AIMarketAnalyzer
        analyzer = AIMarketAnalyzer()
        
        asset_symbols = ["AAPL", "GOOGL"]
        market_data = {"AAPL": {"price": 150.0}, "GOOGL": {"price": 2750.0}}
        result = analyzer.predict_asset_prices(asset_symbols, market_data, "1h")
        
        self.assertEqual(len(result['predictions']), 2)
        self.assertIn('confidence_level', result)
        # Note: The method calls generate_investment_insights, not analyze_market_data directly
    
    @patch('ai.gemini_client.GeminiAIClient.analyze_market_data')
    def test_ai_analysis_fallback_on_error(self, mock_ai_analysis):
        """Test fallback behavior when AI analysis fails"""
        # Mock AI to raise exception
        mock_ai_analysis.side_effect = Exception("AI service unavailable")
        
        from tools.ai_market_analyzer import AIMarketAnalyzer
        analyzer = AIMarketAnalyzer()
        
        # Should handle error gracefully and return fallback response
        result = analyzer.analyze_market_trends(self.mock_market_data)
        
        # Should return an error response when AI fails
        self.assertIsInstance(result, dict)
        self.assertIn('error', result)
        self.assertTrue(result['error'])


class TestAIDecisionMaker(unittest.TestCase):
    """Test cases for AI Decision Maker with Gemini Integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_investment_request = {
            "account_number": "12345",
            "asset_symbol": "AAPL",
            "amount": 1000.0,
            "investment_type": "buy",
            "user_tier": 2
        }
        
        self.mock_market_data = {
            "AAPL": {"price": 150.25, "volatility": 0.15, "trend": "bullish"}
        }
        
        self.mock_user_profile = {
            "risk_tolerance": "medium",
            "investment_goals": ["growth", "income"],
            "time_horizon": "5_years"
        }
        
        self.mock_ai_decision = {
            "recommendation": "approve",
            "confidence_score": 0.85,
            "reasoning": "Strong fundamentals and favorable market conditions",
            "risk_assessment": "medium",
            "expected_return": 0.12
        }
    
    @patch('ai.gemini_client.GeminiAIClient.make_investment_decision')
    def test_ai_investment_decision_success(self, mock_ai_decision):
        """Test successful AI investment decision"""
        mock_ai_decision.return_value = self.mock_ai_decision
        
        from tools.ai_decision_maker import AIDecisionMaker
        decision_maker = AIDecisionMaker()
        
        risk_rules = {"max_investment_amount": 5000, "min_user_tier": 1}
        result = decision_maker.make_investment_decision(
            self.mock_investment_request,
            self.mock_market_data,
            self.mock_user_profile,
            risk_rules
        )
        
        self.assertEqual(result['recommendation'], "approve")
        self.assertEqual(result['confidence_score'], 0.85)
        self.assertIn("decision_timestamp", result)
        mock_ai_decision.assert_called_once()
    
    @patch('ai.gemini_client.GeminiAIClient.analyze_risk')
    def test_ai_risk_assessment_success(self, mock_ai_risk):
        """Test successful AI risk assessment"""
        mock_risk_response = {
            "overall_risk_score": 0.3,
            "risk_factors": ["market_volatility", "concentration_risk"],
            "mitigation_strategies": ["diversification", "stop_loss"],
            "confidence_level": "high"
        }
        mock_ai_risk.return_value = mock_risk_response
        
        from tools.ai_decision_maker import AIDecisionMaker
        decision_maker = AIDecisionMaker()
        
        investment_details = {"symbol": "AAPL", "amount": 1000, "allocation": 0.1}
        market_conditions = {"volatility": 0.15, "trend": "bullish"}
        user_risk_profile = {"tolerance": "medium", "experience": "intermediate"}
        
        result = decision_maker.assess_investment_risk(
            investment_details, market_conditions, user_risk_profile
        )
        
        self.assertEqual(result['overall_risk_score'], 0.3)
        self.assertIn("risk_factors", result)
        self.assertIn("assessment_timestamp", result)
        mock_ai_risk.assert_called_once()
    
    def test_compliance_validation_logic(self):
        """Test compliance validation logic"""
        from tools.ai_decision_maker import AIDecisionMaker
        decision_maker = AIDecisionMaker()
        
        # Test amount limits
        investment_request = {"amount": 1000}
        regulatory_rules = {"max_investment_amount": 5000}
        self.assertTrue(decision_maker._check_amount_limits(investment_request, regulatory_rules))
        
        # Test asset restrictions
        investment_request = {"asset_symbol": "AAPL"}
        regulatory_rules = {"restricted_assets": ["PENNY_STOCK"]}
        self.assertTrue(decision_maker._check_asset_restrictions(investment_request, regulatory_rules))
        
        # Test user eligibility
        investment_request = {"user_tier": 2}
        regulatory_rules = {"min_user_tier": 1}
        self.assertTrue(decision_maker._check_user_eligibility(investment_request, regulatory_rules))


class TestAIPortfolioManager(unittest.TestCase):
    """Test cases for AI Portfolio Manager with Gemini Integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_portfolio = {
            "assets": [
                {"symbol": "AAPL", "weight": 0.4, "sector": "technology", "asset_class": "equity"},
                {"symbol": "GOOGL", "weight": 0.3, "sector": "technology", "asset_class": "equity"},
                {"symbol": "BOND", "weight": 0.3, "sector": "fixed_income", "asset_class": "bond"}
            ],
            "total_value": 100000
        }
        
        self.mock_market_conditions = {
            "volatility": 0.15,
            "trend": "bullish",
            "economic_indicators": {"gdp_growth": 0.03, "inflation": 0.02}
        }
        
        self.mock_ai_optimization = {
            "recommended_allocation": {"equity": 0.6, "bonds": 0.4},
            "diversification_score": 0.85,
            "expected_return": 0.08,
            "expected_risk": 0.12,
            "confidence_level": "high"
        }
    
    @patch('ai.gemini_client.GeminiAIClient.optimize_portfolio')
    def test_ai_portfolio_optimization_success(self, mock_ai_optimization):
        """Test successful AI portfolio optimization"""
        mock_ai_optimization.return_value = self.mock_ai_optimization
        
        from tools.ai_portfolio_manager import AIPortfolioManager
        portfolio_manager = AIPortfolioManager()
        
        user_goals = {"goals": ["growth", "income"], "time_horizon": "5_years"}
        result = portfolio_manager.optimize_portfolio(
            self.mock_portfolio,
            self.mock_market_conditions,
            user_goals,
            "medium"
        )
        
        self.assertEqual(result['diversification_score'], 0.85)
        self.assertEqual(result['expected_return'], 0.08)
        self.assertIn("optimization_timestamp", result)
        mock_ai_optimization.assert_called_once()
    
    def test_diversification_score_calculation(self):
        """Test diversification score calculation"""
        from tools.ai_portfolio_manager import AIPortfolioManager
        portfolio_manager = AIPortfolioManager()
        
        # Test well-diversified portfolio
        diversified_portfolio = {
            "assets": [
                {"weight": 0.25}, {"weight": 0.25}, {"weight": 0.25}, {"weight": 0.25}
            ]
        }
        score = portfolio_manager._calculate_diversification_score(diversified_portfolio)
        self.assertGreaterEqual(score, 0.7)
        
        # Test concentrated portfolio
        concentrated_portfolio = {
            "assets": [
                {"weight": 0.8}, {"weight": 0.2}
            ]
        }
        score = portfolio_manager._calculate_diversification_score(concentrated_portfolio)
        self.assertLess(score, 0.5)
    
    def test_sector_allocation_analysis(self):
        """Test sector allocation analysis"""
        from tools.ai_portfolio_manager import AIPortfolioManager
        portfolio_manager = AIPortfolioManager()
        
        portfolio_data = {
            "assets": [
                {"sector": "technology", "weight": 0.6},
                {"sector": "healthcare", "weight": 0.3},
                {"sector": "finance", "weight": 0.1}
            ]
        }
        
        sector_allocation = portfolio_manager._analyze_sector_allocation(portfolio_data)
        
        self.assertEqual(sector_allocation["technology"], 0.6)
        self.assertEqual(sector_allocation["healthcare"], 0.3)
        self.assertEqual(sector_allocation["finance"], 0.1)
    
    def test_concentration_risk_assessment(self):
        """Test concentration risk assessment"""
        from tools.ai_portfolio_manager import AIPortfolioManager
        portfolio_manager = AIPortfolioManager()
        
        # High concentration
        high_concentration = {
            "assets": [{"weight": 0.5}, {"weight": 0.3}, {"weight": 0.2}]
        }
        risk = portfolio_manager._assess_concentration_risk(high_concentration)
        self.assertEqual(risk, "high")
        
        # Low concentration
        low_concentration = {
            "assets": [{"weight": 0.2}, {"weight": 0.2}, {"weight": 0.2}, {"weight": 0.2}, {"weight": 0.2}]
        }
        risk = portfolio_manager._assess_concentration_risk(low_concentration)
        self.assertEqual(risk, "low")


class TestGeminiAIClient(unittest.TestCase):
    """Test cases for Gemini AI Client"""
    
    def setUp(self):
        """Set up test fixtures"""
        os.environ['GEMINI_API_KEY'] = 'test-api-key'
    
    @patch('google.generativeai.GenerativeModel.generate_content')
    def test_gemini_content_generation_success(self, mock_generate):
        """Test successful content generation with Gemini"""
        mock_response = Mock()
        mock_response.text = '{"trend_analysis": "bullish", "confidence_score": 85}'
        mock_generate.return_value = mock_response
        
        from ai.gemini_client import GeminiAIClient
        client = GeminiAIClient()
        
        result = client.analyze_market_data({"symbol": "AAPL", "price": 150.0})
        
        self.assertEqual(result['trend_analysis'], "bullish")
        self.assertEqual(result['confidence_score'], 85)
        mock_generate.assert_called_once()
    
    @patch('google.generativeai.GenerativeModel.generate_content')
    def test_gemini_content_generation_failure(self, mock_generate):
        """Test content generation failure handling"""
        mock_generate.side_effect = Exception("API rate limit exceeded")
        
        from ai.gemini_client import GeminiAIClient
        client = GeminiAIClient()
        
        # Should handle error gracefully and return error response
        result = client.analyze_market_data({"symbol": "AAPL", "price": 150.0})
        
        # Should return an error response when API fails
        self.assertIsInstance(result, dict)
        self.assertIn('error', result)
    
    def test_gemini_client_initialization_without_api_key(self):
        """Test Gemini client initialization without API key"""
        # Remove API key from environment
        if 'GEMINI_API_KEY' in os.environ:
            del os.environ['GEMINI_API_KEY']
        
        from ai.gemini_client import GeminiAIClient
        
        with self.assertRaises(ValueError) as context:
            GeminiAIClient()
        
        self.assertIn("Gemini API key not provided", str(context.exception))


if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestMarketAnalyzer))
    test_suite.addTest(unittest.makeSuite(TestRuleValidator))
    test_suite.addTest(unittest.makeSuite(TestOrderExecutor))
    test_suite.addTest(unittest.makeSuite(TestAssetDatabaseClient))
    test_suite.addTest(unittest.makeSuite(TestAIMarketAnalyzer))
    test_suite.addTest(unittest.makeSuite(TestAIDecisionMaker))
    test_suite.addTest(unittest.makeSuite(TestAIPortfolioManager))
    test_suite.addTest(unittest.makeSuite(TestGeminiAIClient))
    
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
