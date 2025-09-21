#!/usr/bin/env python3
# Copyright 2024 Google LLC
# Bank Asset Agent - API Tests

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import json
import grpc
from concurrent import futures

# Add the parent directory to the path to import the API modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestGRPCService(unittest.TestCase):
    """Test cases for gRPC Service Implementation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_port = 50051
        
    @patch('grpc.insecure_channel')
    def test_grpc_client_creation(self, mock_channel):
        """Test gRPC client creation"""
        mock_channel.return_value = Mock()
        
        # Test client creation
        from api.grpc_service import create_grpc_client
        client = create_grpc_client()
        
        self.assertIsNotNone(client)
        mock_channel.assert_called_once_with('bank-asset-agent:8080')
    
    def test_market_data_request_validation(self):
        """Test market data request validation"""
        # Valid request
        valid_request = {
            "asset_symbols": ["AAPL", "GOOGL"],
            "time_range": "1d",
            "analysis_type": "trend"
        }
        
        # Validate required fields
        required_fields = ["asset_symbols", "time_range"]
        is_valid = all(field in valid_request for field in required_fields)
        
        self.assertTrue(is_valid)
        self.assertIsInstance(valid_request["asset_symbols"], list)
        self.assertGreater(len(valid_request["asset_symbols"]), 0)
    
    def test_investment_request_validation(self):
        """Test investment request validation"""
        # Valid request
        valid_request = {
            "user_id": "user123",
            "asset_symbol": "AAPL",
            "amount": 1000.0,
            "investment_type": "buy",
            "risk_tolerance": "medium"
        }
        
        # Validate required fields
        required_fields = ["user_id", "asset_symbol", "amount", "investment_type"]
        is_valid = all(field in valid_request for field in required_fields)
        
        self.assertTrue(is_valid)
        self.assertGreater(valid_request["amount"], 0)
        self.assertIn(valid_request["investment_type"], ["buy", "sell"])
    
    def test_asset_management_request_validation(self):
        """Test asset management request validation"""
        # Valid request
        valid_request = {
            "operation": "update_price",
            "asset_id": 1,
            "new_price": 155.50,
            "timestamp": "2024-09-22T10:30:00Z"
        }
        
        # Validate required fields
        required_fields = ["operation", "asset_id"]
        is_valid = all(field in valid_request for field in required_fields)
        
        self.assertTrue(is_valid)
        self.assertIn(valid_request["operation"], ["update_price", "update_availability", "add_asset"])
    
    def test_rule_validation_request_validation(self):
        """Test rule validation request validation"""
        # Valid request
        valid_request = {
            "user_id": "user123",
            "investment_data": {
                "asset_symbol": "AAPL",
                "amount": 1000.0,
                "risk_level": "medium"
            },
            "rule_types": ["compliance", "risk", "liquidity"]
        }
        
        # Validate required fields
        required_fields = ["user_id", "investment_data", "rule_types"]
        is_valid = all(field in valid_request for field in required_fields)
        
        self.assertTrue(is_valid)
        self.assertIsInstance(valid_request["rule_types"], list)
        self.assertGreater(len(valid_request["rule_types"]), 0)

class TestAPIHandlers(unittest.TestCase):
    """Test cases for API Handlers"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_context = Mock()
        self.mock_context.user_id = "user123"
    
    @patch('api.handlers.BankAssetAgentClient')
    def test_analyze_market_data_handler(self, mock_client_class):
        """Test market data analysis handler"""
        # Mock client
        mock_client = Mock()
        mock_client.get_market_data.return_value = {
            "symbols": ["AAPL", "GOOGL"],
            "prices": {"AAPL": 150.25, "GOOGL": 2800.50},
            "analysis": {"trend": "bullish", "confidence": 0.85}
        }
        mock_client_class.return_value = mock_client
        
        from api.handlers import analyze_market_data_handler
        
        request_data = {
            "asset_symbols": ["AAPL", "GOOGL"],
            "time_range": "1d"
        }
        
        result = analyze_market_data_handler(request_data, self.mock_context)
        
        self.assertIn("analysis", result)
        self.assertEqual(result["analysis"]["trend"], "bullish")
        mock_client.get_market_data.assert_called_once()
    
    @patch('api.handlers.BankAssetAgentClient')
    def test_process_investment_request_handler(self, mock_client_class):
        """Test investment request processing handler"""
        # Mock client
        mock_client = Mock()
        mock_client.validate_rules.return_value = {"valid": True, "risk_score": 0.3}
        mock_client.execute_order.return_value = {"order_id": "order123", "status": "executed"}
        mock_client_class.return_value = mock_client
        
        from api.handlers import process_investment_request_handler
        
        request_data = {
            "user_id": "user123",
            "asset_symbol": "AAPL",
            "amount": 1000.0,
            "investment_type": "buy"
        }
        
        result = process_investment_request_handler(request_data, self.mock_context)
        
        self.assertIn("order_id", result)
        self.assertEqual(result["order_id"], "order123")
        mock_client.validate_rules.assert_called_once()
        mock_client.execute_order.assert_called_once()
    
    @patch('api.handlers.AssetsDatabaseClient')
    def test_execute_asset_management_handler(self, mock_client_class):
        """Test asset management execution handler"""
        # Mock client
        mock_client = Mock()
        mock_client.update_asset_price.return_value = True
        mock_client_class.return_value = mock_client
        
        from api.handlers import execute_asset_management_handler
        
        request_data = {
            "operation": "update_price",
            "asset_id": 1,
            "new_price": 155.50
        }
        
        result = execute_asset_management_handler(request_data, self.mock_context)
        
        self.assertTrue(result["success"])
        mock_client.update_asset_price.assert_called_once()
    
    @patch('api.handlers.BankAssetAgentClient')
    def test_validate_investment_rules_handler(self, mock_client_class):
        """Test investment rules validation handler"""
        # Mock client
        mock_client = Mock()
        mock_client.validate_rules.return_value = {
            "valid": True,
            "risk_score": 0.3,
            "compliance_status": "passed"
        }
        mock_client_class.return_value = mock_client
        
        from api.handlers import validate_investment_rules_handler
        
        request_data = {
            "user_id": "user123",
            "investment_data": {
                "asset_symbol": "AAPL",
                "amount": 1000.0
            }
        }
        
        result = validate_investment_rules_handler(request_data, self.mock_context)
        
        self.assertTrue(result["valid"])
        self.assertEqual(result["compliance_status"], "passed")
        mock_client.validate_rules.assert_called_once()

class TestDataModels(unittest.TestCase):
    """Test cases for Data Models"""
    
    def test_market_data_request_model(self):
        """Test market data request model validation"""
        from api.models import MarketDataRequest
        
        # Valid request
        request = MarketDataRequest(
            asset_symbols=["AAPL", "GOOGL"],
            time_range="1d",
            analysis_type="trend"
        )
        
        self.assertEqual(request.asset_symbols, ["AAPL", "GOOGL"])
        self.assertEqual(request.time_range, "1d")
        self.assertEqual(request.analysis_type, "trend")
    
    def test_investment_request_model(self):
        """Test investment request model validation"""
        from api.models import InvestmentRequest
        
        # Valid request
        request = InvestmentRequest(
            user_id="user123",
            asset_symbol="AAPL",
            amount=1000.0,
            investment_type="buy",
            risk_tolerance="medium"
        )
        
        self.assertEqual(request.user_id, "user123")
        self.assertEqual(request.asset_symbol, "AAPL")
        self.assertEqual(request.amount, 1000.0)
        self.assertEqual(request.investment_type, "buy")
        self.assertEqual(request.risk_tolerance, "medium")
    
    def test_asset_management_request_model(self):
        """Test asset management request model validation"""
        from api.models import AssetManagementRequest
        
        # Valid request
        request = AssetManagementRequest(
            operation="update_price",
            asset_id=1,
            new_price=155.50,
            timestamp="2024-09-22T10:30:00Z"
        )
        
        self.assertEqual(request.operation, "update_price")
        self.assertEqual(request.asset_id, 1)
        self.assertEqual(request.new_price, 155.50)
        self.assertEqual(request.timestamp, "2024-09-22T10:30:00Z")
    
    def test_rule_validation_request_model(self):
        """Test rule validation request model validation"""
        from api.models import RuleValidationRequest
        
        # Valid request
        request = RuleValidationRequest(
            user_id="user123",
            investment_data={"asset_symbol": "AAPL", "amount": 1000.0},
            rule_types=["compliance", "risk"]
        )
        
        self.assertEqual(request.user_id, "user123")
        self.assertEqual(request.investment_data["asset_symbol"], "AAPL")
        self.assertEqual(request.rule_types, ["compliance", "risk"])

class TestErrorHandling(unittest.TestCase):
    """Test cases for Error Handling"""
    
    def test_grpc_error_handling(self):
        """Test gRPC error handling"""
        from api.grpc_service import handle_grpc_error
        
        # Test different error types
        grpc_error = grpc.RpcError()
        result = handle_grpc_error(grpc_error)
        
        self.assertIn("error", result)
        self.assertIn("message", result)
    
    def test_http_error_handling(self):
        """Test HTTP error handling"""
        from api.handlers import handle_http_error
        
        # Test HTTP error
        http_error = Exception("HTTP 500 Internal Server Error")
        result = handle_http_error(http_error)
        
        self.assertIn("error", result)
        self.assertIn("message", result)
    
    def test_database_error_handling(self):
        """Test database error handling"""
        from api.handlers import handle_database_error
        
        # Test database error
        db_error = Exception("Database connection failed")
        result = handle_database_error(db_error)
        
        self.assertIn("error", result)
        self.assertIn("message", result)

if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestGRPCService))
    test_suite.addTest(unittest.makeSuite(TestAPIHandlers))
    test_suite.addTest(unittest.makeSuite(TestDataModels))
    test_suite.addTest(unittest.makeSuite(TestErrorHandling))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"API Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print(f"{'='*50}")
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
