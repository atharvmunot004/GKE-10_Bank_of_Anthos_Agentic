#!/usr/bin/env python3
"""
Unit tests for User Tier Agent Service
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import jwt
from datetime import datetime, timedelta
import sys
import os

# Add the parent directory to the path to import the main module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from user_tier_agent import UserTierAgent, app

class TestUserTierAgent(unittest.TestCase):
    """Test cases for UserTierAgent class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.agent = UserTierAgent()
        self.valid_jwt_token = jwt.encode({
            'account': '1234567890',
            'exp': datetime.utcnow() + timedelta(hours=1)
        }, 'test-secret', algorithm='HS256')
        
        self.mock_transactions = [
            {
                'amount': 50000,  # $500.00 in cents
                'timestamp': datetime.now() - timedelta(days=1),
                'fromAccountNum': '1234567890',
                'toAccountNum': '9876543210',
                'uuid': 'test-uuid-1'
            },
            {
                'amount': 25000,  # $250.00 in cents
                'timestamp': datetime.now() - timedelta(days=2),
                'fromAccountNum': '1234567890',
                'toAccountNum': '9876543210',
                'uuid': 'test-uuid-2'
            }
        ]
    
    @patch('user_tier_agent.JWT_SECRET_KEY', 'test-secret')
    def test_validate_jwt_token_valid(self):
        """Test JWT token validation with valid token."""
        token = f"Bearer {self.valid_jwt_token}"
        result = self.agent.validate_jwt_token(token)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['account'], '1234567890')
    
    def test_validate_jwt_token_invalid_format(self):
        """Test JWT token validation with invalid format."""
        result = self.agent.validate_jwt_token("invalid-token")
        self.assertIsNone(result)
    
    def test_validate_jwt_token_expired(self):
        """Test JWT token validation with expired token."""
        expired_token = jwt.encode({
            'account': '1234567890',
            'exp': datetime.utcnow() - timedelta(hours=1)
        }, 'test-secret', algorithm='HS256')
        
        token = f"Bearer {expired_token}"
        result = self.agent.validate_jwt_token(token)
        self.assertIsNone(result)
    
    @patch('user_tier_agent.psycopg2.connect')
    def test_get_user_transaction_history(self, mock_connect):
        """Test retrieving user transaction history."""
        # Mock database connection and cursor
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = self.mock_transactions
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        result = self.agent.get_user_transaction_history('1234567890', 10)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['amount'], 50000)
        mock_cursor.execute.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()
    
    def test_format_transaction_data(self):
        """Test formatting transaction data."""
        formatted = self.agent.format_transaction_data(self.mock_transactions)
        
        self.assertEqual(len(formatted), 2)
        self.assertEqual(formatted[0][0], 500.0)  # Converted from cents
        self.assertIsInstance(formatted[0][1], str)  # ISO format timestamp
    
    def test_generate_tier_allocation_prompt(self):
        """Test generating tier allocation prompt."""
        uuid = "test-uuid"
        transaction_data = [(500.0, "2024-01-01T10:00:00"), (250.0, "2024-01-02T10:00:00")]
        amount_break = 1000.0
        
        prompt = self.agent.generate_tier_allocation_prompt(uuid, transaction_data, amount_break)
        
        self.assertIn(uuid, prompt)
        self.assertIn("500.0", prompt)
        self.assertIn("250.0", prompt)
        self.assertIn(str(amount_break), prompt)
        self.assertIn("Tier1", prompt)
        self.assertIn("Tier2", prompt)
        self.assertIn("Tier3", prompt)
    
    def test_validate_allocation_response_valid(self):
        """Test validating a valid allocation response."""
        valid_allocation = {
            "tier1": 30.0,
            "tier2": 50.0,
            "tier3": 20.0,
            "reasoning": "Test allocation"
        }
        
        result = self.agent.validate_allocation_response(valid_allocation)
        self.assertTrue(result)
    
    def test_validate_allocation_response_invalid_percentages(self):
        """Test validating an invalid allocation response (wrong percentages)."""
        invalid_allocation = {
            "tier1": 30.0,
            "tier2": 50.0,
            "tier3": 30.0,  # Total is 110%, not 100%
            "reasoning": "Test allocation"
        }
        
        result = self.agent.validate_allocation_response(invalid_allocation)
        self.assertFalse(result)
    
    def test_validate_allocation_response_missing_keys(self):
        """Test validating an allocation response with missing keys."""
        invalid_allocation = {
            "tier1": 30.0,
            "tier2": 50.0
            # Missing tier3
        }
        
        result = self.agent.validate_allocation_response(invalid_allocation)
        self.assertFalse(result)
    
    def test_get_default_allocation(self):
        """Test getting default allocation."""
        allocation = self.agent.get_default_allocation()
        
        self.assertEqual(allocation["tier1"], 30.0)
        self.assertEqual(allocation["tier2"], 50.0)
        self.assertEqual(allocation["tier3"], 20.0)
        self.assertIn("reasoning", allocation)
    
    def test_calculate_tier_amounts(self):
        """Test calculating tier amounts from percentages."""
        amount_break = 1000.0
        allocation = {
            "tier1": 30.0,
            "tier2": 50.0,
            "tier3": 20.0
        }
        
        amounts = self.agent.calculate_tier_amounts(amount_break, allocation)
        
        self.assertEqual(amounts["tier1"], 300.0)
        self.assertEqual(amounts["tier2"], 500.0)
        self.assertEqual(amounts["tier3"], 200.0)
    
    @patch('user_tier_agent.requests.post')
    def test_call_gemini_api_success(self, mock_post):
        """Test successful Gemini API call."""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            'candidates': [{
                'content': {
                    'parts': [{
                        'text': '{"tier1": 40.0, "tier2": 40.0, "tier3": 20.0, "reasoning": "AI allocation"}'
                    }]
                }
            }]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Set API key
        self.agent.gemini_api_key = "test-api-key"
        
        prompt = "Test prompt"
        result = self.agent.call_gemini_api(prompt)
        
        self.assertEqual(result["tier1"], 40.0)
        self.assertEqual(result["tier2"], 40.0)
        self.assertEqual(result["tier3"], 20.0)
        self.assertEqual(result["reasoning"], "AI allocation")
    
    @patch('user_tier_agent.requests.post')
    def test_call_gemini_api_failure(self, mock_post):
        """Test Gemini API call failure falls back to default."""
        # Mock API failure
        mock_post.side_effect = Exception("API Error")
        
        # Set API key
        self.agent.gemini_api_key = "test-api-key"
        
        prompt = "Test prompt"
        result = self.agent.call_gemini_api(prompt)
        
        # Should return default allocation
        self.assertEqual(result["tier1"], 30.0)
        self.assertEqual(result["tier2"], 50.0)
        self.assertEqual(result["tier3"], 20.0)
    
    def test_call_gemini_api_no_key(self):
        """Test Gemini API call without API key returns default."""
        self.agent.gemini_api_key = ""
        
        prompt = "Test prompt"
        result = self.agent.call_gemini_api(prompt)
        
        # Should return default allocation
        self.assertEqual(result["tier1"], 30.0)
        self.assertEqual(result["tier2"], 50.0)
        self.assertEqual(result["tier3"], 20.0)
    
    @patch.object(UserTierAgent, 'get_user_transaction_history')
    @patch.object(UserTierAgent, 'call_gemini_api')
    def test_process_allocation_request_success(self, mock_gemini, mock_transactions):
        """Test successful allocation request processing."""
        # Mock dependencies
        mock_transactions.return_value = self.mock_transactions
        mock_gemini.return_value = {
            "tier1": 35.0,
            "tier2": 45.0,
            "tier3": 20.0,
            "reasoning": "AI-generated allocation"
        }
        
        # Mock JWT validation
        with patch.object(self.agent, 'validate_jwt_token') as mock_jwt:
            mock_jwt.return_value = {'account': '1234567890'}
            
            request_data = {
                'accountid': '1234567890',
                'amount': 1000.0,
                'uuid': 'test-uuid',
                'purpose': 'INVEST'
            }
            
            result = self.agent.process_allocation_request(request_data, f"Bearer {self.valid_jwt_token}")
            
            self.assertEqual(result['accountid'], '1234567890')
            self.assertEqual(result['amount'], 1000.0)
            self.assertEqual(result['uuid'], 'test-uuid')
            self.assertEqual(result['purpose'], 'INVEST')
            self.assertEqual(result['tier1'], 350.0)
            self.assertEqual(result['tier2'], 450.0)
            self.assertEqual(result['tier3'], 200.0)
            self.assertIn('timestamp', result)
    
    def test_process_allocation_request_invalid_jwt(self):
        """Test allocation request with invalid JWT."""
        with patch.object(self.agent, 'validate_jwt_token') as mock_jwt:
            mock_jwt.return_value = None
            
            request_data = {
                'accountid': '1234567890',
                'amount': 1000.0,
                'uuid': 'test-uuid'
            }
            
            with self.assertRaises(ValueError) as context:
                self.agent.process_allocation_request(request_data, "Bearer invalid-token")
            
            self.assertIn("Invalid or expired JWT token", str(context.exception))
    
    def test_process_allocation_request_missing_params(self):
        """Test allocation request with missing parameters."""
        with patch.object(self.agent, 'validate_jwt_token') as mock_jwt:
            mock_jwt.return_value = {'account': '1234567890'}
            
            request_data = {
                'accountid': '1234567890',
                # Missing amount and uuid
            }
            
            with self.assertRaises(ValueError) as context:
                self.agent.process_allocation_request(request_data, f"Bearer {self.valid_jwt_token}")
            
            self.assertIn("Missing required parameters", str(context.exception))


class TestUserTierAgentAPI(unittest.TestCase):
    """Test cases for Flask API endpoints."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = app.test_client()
        self.valid_jwt_token = jwt.encode({
            'account': '1234567890',
            'exp': datetime.utcnow() + timedelta(hours=1)
        }, 'test-secret', algorithm='HS256')
    
    def test_health_endpoint(self):
        """Test health endpoint."""
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'user-tier-agent')
    
    @patch('user_tier_agent.UserTierAgent.get_db_connection')
    def test_ready_endpoint_success(self, mock_connect):
        """Test readiness endpoint with successful database connection."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        response = self.app.get('/ready')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'ready')
        self.assertEqual(data['service'], 'user-tier-agent')
    
    def test_status_endpoint(self):
        """Test status endpoint."""
        response = self.app.get('/api/v1/status')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'operational')
        self.assertEqual(data['service'], 'user-tier-agent')
        self.assertIn('configuration', data)
        self.assertIn('endpoints', data)
    
    @patch('user_tier_agent.UserTierAgent.process_allocation_request')
    def test_allocate_endpoint_success(self, mock_process):
        """Test successful allocation endpoint."""
        mock_process.return_value = {
            'accountid': '1234567890',
            'amount': 1000.0,
            'uuid': 'test-uuid',
            'purpose': 'INVEST',
            'tier1': 350.0,
            'tier2': 450.0,
            'tier3': 200.0
        }
        
        headers = {'Authorization': f'Bearer {self.valid_jwt_token}'}
        data = {
            'accountid': '1234567890',
            'amount': 1000.0,
            'uuid': 'test-uuid',
            'purpose': 'INVEST'
        }
        
        response = self.app.post('/api/v1/allocate', 
                               json=data, 
                               headers=headers)
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.data)
        self.assertEqual(response_data['status'], 'success')
        self.assertIn('data', response_data)
    
    def test_allocate_endpoint_missing_auth(self):
        """Test allocation endpoint without authorization header."""
        data = {
            'accountid': '1234567890',
            'amount': 1000.0,
            'uuid': 'test-uuid'
        }
        
        response = self.app.post('/api/v1/allocate', json=data)
        self.assertEqual(response.status_code, 401)
        
        response_data = json.loads(response.data)
        self.assertIn('Missing Authorization header', response_data['error'])
    
    def test_allocate_endpoint_missing_body(self):
        """Test allocation endpoint without request body."""
        headers = {
            'Authorization': f'Bearer {self.valid_jwt_token}',
            'Content-Type': 'application/json'
        }
        
        response = self.app.post('/api/v1/allocate', headers=headers)
        # Flask returns 500 for missing JSON body, but our error handler catches it
        self.assertIn(response.status_code, [400, 500])
        
        response_data = json.loads(response.data)
        # Check for any error message indicating the request was invalid
        self.assertIn('error', response_data)
        self.assertIsInstance(response_data['error'], str)
        self.assertTrue(len(response_data['error']) > 0)


if __name__ == '__main__':
    unittest.main()
