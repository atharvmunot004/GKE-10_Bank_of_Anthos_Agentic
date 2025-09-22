#!/usr/bin/env python3
"""
Unit tests for investment-manager-svc
"""

import unittest
import json
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add the parent directory to the path to import the main module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock requests before importing the main module
sys.modules['requests'] = Mock()

# Now import the main module
from investment_manager import app

class TestInvestmentManager(unittest.TestCase):
    """Test cases for Investment Manager Service."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
    
    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
    
    def test_ready_endpoint(self):
        """Test readiness check endpoint."""
        response = self.client.get('/ready')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'ready')
    
    @patch('investment_manager.requests.get')
    def test_get_portfolio_success(self, mock_get):
        """Test successful portfolio retrieval."""
        # Mock the portfolio-reader-svc response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "portfolio": {
                "accountid": "1234567890",
                "tier1_allocation": 60.0,
                "tier2_allocation": 30.0,
                "tier3_allocation": 10.0,
                "tier1_value": 6000.0,
                "tier2_value": 3000.0,
                "tier3_value": 1000.0
            },
            "transactions": []
        }
        mock_get.return_value = mock_response
        
        response = self.client.get('/api/v1/portfolio/1234567890')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('portfolio', data)
        self.assertEqual(data['portfolio']['accountid'], '1234567890')
    
    @patch('investment_manager.requests.get')
    def test_get_portfolio_service_unavailable(self, mock_get):
        """Test portfolio retrieval when service is unavailable."""
        mock_get.side_effect = Exception("Service unavailable")
        
        response = self.client.get('/api/v1/portfolio/1234567890')
        self.assertEqual(response.status_code, 503)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    @patch('investment_manager.requests.get')
    def test_get_portfolio_transactions_success(self, mock_get):
        """Test successful portfolio transactions retrieval."""
        # Mock the portfolio-reader-svc response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "uuid": "transaction-uuid-1",
                "tier1_change": 100.0,
                "tier2_change": 50.0,
                "tier3_change": 25.0,
                "status": "COMPLETED"
            }
        ]
        mock_get.return_value = mock_response
        
        response = self.client.get('/api/v1/portfolio/1234567890/transactions')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['uuid'], 'transaction-uuid-1')
    
    @patch('investment_manager.requests.post')
    def test_invest_success(self, mock_post):
        """Test successful investment processing."""
        # Mock invest-svc response
        invest_response = Mock()
        invest_response.status_code = 200
        invest_response.json.return_value = {"status": "done"}
        
        # Mock ledger-writer response
        ledger_response = Mock()
        ledger_response.status_code = 200
        
        mock_post.side_effect = [invest_response, ledger_response]
        
        response = self.client.post('/api/v1/invest', 
                                  json={"accountid": "1234567890", "amount": 1000.0})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertTrue(data['ledger_recorded'])
    
    @patch('investment_manager.requests.post')
    def test_invest_failed(self, mock_post):
        """Test investment processing failure."""
        # Mock invest-svc response
        invest_response = Mock()
        invest_response.status_code = 200
        invest_response.json.return_value = {"status": "failed", "message": "Insufficient funds"}
        
        mock_post.return_value = invest_response
        
        response = self.client.post('/api/v1/invest', 
                                  json={"accountid": "1234567890", "amount": 1000.0})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'failed')
    
    @patch('investment_manager.requests.post')
    def test_withdraw_success(self, mock_post):
        """Test successful withdrawal processing."""
        # Mock withdraw-svc response
        withdraw_response = Mock()
        withdraw_response.status_code = 200
        withdraw_response.json.return_value = {"status": "done"}
        
        # Mock ledger-writer response
        ledger_response = Mock()
        ledger_response.status_code = 200
        
        mock_post.side_effect = [withdraw_response, ledger_response]
        
        response = self.client.post('/api/v1/withdraw', 
                                  json={"accountid": "1234567890", "amount": 500.0})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertTrue(data['ledger_recorded'])
    
    def test_invest_invalid_data(self):
        """Test investment with invalid data."""
        response = self.client.post('/api/v1/invest', 
                                  json={"accountid": "", "amount": -100.0})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_withdraw_invalid_data(self):
        """Test withdrawal with invalid data."""
        response = self.client.post('/api/v1/withdraw', 
                                  json={"accountid": "", "amount": -100.0})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    @patch('investment_manager.requests.get')
    def test_status_endpoint(self, mock_get):
        """Test status endpoint with dependency checks."""
        # Mock all dependency responses
        mock_responses = [Mock() for _ in range(4)]
        for mock_resp in mock_responses:
            mock_resp.status_code = 200
        
        mock_get.side_effect = mock_responses
        
        response = self.client.get('/api/v1/status')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['service'], 'investment-manager-svc')
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('dependencies', data)

def run_tests():
    """Run all tests and return results."""
    print("🧪 Running Investment Manager Service Unit Tests")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestInvestmentManager))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print(f"✅ Tests Run: {result.testsRun}")
    print(f"✅ Failures: {len(result.failures)}")
    print(f"✅ Errors: {len(result.errors)}")
    print(f"✅ Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n❌ Errors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
