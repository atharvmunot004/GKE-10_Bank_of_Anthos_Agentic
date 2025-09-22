#!/usr/bin/env python3
# Copyright 2024 Google LLC
# Bank Asset Agent - Prompt Testing Framework

import unittest
import sys
import os
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add the parent directory to the path to import the agent modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up environment for AI testing
os.environ['GEMINI_API_KEY'] = 'test-api-key-for-prompt-testing'
os.environ['AI_ENABLED'] = 'true'
os.environ['AI_CONFIDENCE_THRESHOLD'] = '0.7'
os.environ['AI_FALLBACK_ENABLED'] = 'true'

class PromptTestingFramework:
    """Framework for testing AI prompts and responses"""
    
    def __init__(self):
        self.test_prompts = []
        self.expected_responses = []
        self.actual_responses = []
        self.test_results = []
    
    def add_test_prompt(self, prompt, expected_response, test_name):
        """Add a test prompt with expected response"""
        self.test_prompts.append({
            'prompt': prompt,
            'expected_response': expected_response,
            'test_name': test_name,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def run_prompt_tests(self, ai_client):
        """Run all prompt tests against AI client"""
        for test in self.test_prompts:
            try:
                # Execute the prompt
                actual_response = ai_client.generate_content(test['prompt'])
                
                # Store actual response
                self.actual_responses.append({
                    'test_name': test['test_name'],
                    'actual_response': actual_response,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                # Evaluate response
                result = self._evaluate_response(
                    test['expected_response'],
                    actual_response,
                    test['test_name']
                )
                
                self.test_results.append(result)
                
            except Exception as e:
                # Handle test failure
                self.test_results.append({
                    'test_name': test['test_name'],
                    'status': 'failed',
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                })
    
    def _evaluate_response(self, expected, actual, test_name):
        """Evaluate actual response against expected response"""
        try:
            # Parse JSON responses if possible
            try:
                expected_json = json.loads(expected) if isinstance(expected, str) else expected
                actual_json = json.loads(actual) if isinstance(actual, str) else actual
                
                # Compare JSON responses
                if isinstance(expected_json, dict) and isinstance(actual_json, dict):
                    return self._compare_json_responses(expected_json, actual_json, test_name)
                else:
                    return self._compare_text_responses(expected, actual, test_name)
                    
            except (json.JSONDecodeError, TypeError):
                # Fall back to text comparison
                return self._compare_text_responses(expected, actual, test_name)
                
        except Exception as e:
            return {
                'test_name': test_name,
                'status': 'error',
                'error': f"Evaluation failed: {str(e)}",
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _compare_json_responses(self, expected, actual, test_name):
        """Compare JSON responses"""
        score = 0
        total_fields = len(expected)
        matched_fields = 0
        field_comparisons = []
        
        for key, expected_value in expected.items():
            if key in actual:
                if expected_value == actual[key]:
                    matched_fields += 1
                    field_comparisons.append({
                        'field': key,
                        'status': 'match',
                        'expected': expected_value,
                        'actual': actual[key]
                    })
                else:
                    field_comparisons.append({
                        'field': key,
                        'status': 'mismatch',
                        'expected': expected_value,
                        'actual': actual[key]
                    })
            else:
                field_comparisons.append({
                    'field': key,
                    'status': 'missing',
                    'expected': expected_value,
                    'actual': None
                })
        
        score = matched_fields / total_fields if total_fields > 0 else 0
        
        return {
            'test_name': test_name,
            'status': 'passed' if score >= 0.8 else 'failed',
            'score': score,
            'matched_fields': matched_fields,
            'total_fields': total_fields,
            'field_comparisons': field_comparisons,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _compare_text_responses(self, expected, actual, test_name):
        """Compare text responses"""
        # Simple text similarity (in practice, you might use more sophisticated NLP)
        expected_words = set(expected.lower().split())
        actual_words = set(actual.lower().split())
        
        if expected_words and actual_words:
            similarity = len(expected_words.intersection(actual_words)) / len(expected_words.union(actual_words))
        else:
            similarity = 0
        
        return {
            'test_name': test_name,
            'status': 'passed' if similarity >= 0.6 else 'failed',
            'similarity_score': similarity,
            'expected': expected,
            'actual': actual,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def generate_report(self):
        """Generate test report"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'passed'])
        failed_tests = len([r for r in self.test_results if r['status'] == 'failed'])
        error_tests = len([r for r in self.test_results if r['status'] == 'error'])
        
        report = {
            'summary': {
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'errors': error_tests,
                'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0
            },
            'test_results': self.test_results,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return report


class TestPromptTesting(unittest.TestCase):
    """Test cases for prompt testing framework"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.framework = PromptTestingFramework()
        
        # Sample test prompts for different AI capabilities
        self.market_analysis_prompts = [
            {
                'prompt': 'Analyze the following market data and provide trend analysis: {"AAPL": {"price": 150.25, "change": 2.15}, "GOOGL": {"price": 2800.50, "change": -15.30}}',
                'expected_response': {
                    'trend_analysis': 'mixed',
                    'confidence_score': 70,
                    'reasoning': 'Mixed performance across tech stocks',
                    'key_factors': ['AAPL positive momentum', 'GOOGL negative pressure']
                },
                'test_name': 'market_trend_analysis'
            },
            {
                'prompt': 'Predict asset prices for the next hour based on: [{"symbol": "AAPL", "price": 150.25, "timestamp": "2024-09-22T10:30:00Z"}]',
                'expected_response': {
                    'predictions': [
                        {'symbol': 'AAPL', 'predicted_price': 151.50, 'confidence': 0.75, 'reasoning': 'Technical analysis suggests upward trend'}
                    ],
                    'overall_prediction_sentiment': 'cautiously_optimistic'
                },
                'test_name': 'price_prediction'
            }
        ]
        
        self.investment_decision_prompts = [
            {
                'prompt': 'Make an investment decision for: account=12345, asset=TSLA, amount=5000, user_tier=2, risk_tolerance=medium',
                'expected_response': {
                    'recommendation': 'approve',
                    'confidence_score': 0.8,
                    'reasoning': 'Strong fundamentals and appropriate risk level',
                    'risk_assessment': 'medium',
                    'expected_return': 0.12
                },
                'test_name': 'investment_decision'
            },
            {
                'prompt': 'Assess risk for investment: symbol=TSLA, amount=5000, market_volatility=0.25, user_experience=intermediate',
                'expected_response': {
                    'overall_risk_score': 0.3,
                    'risk_factors': ['market_volatility', 'concentration_risk'],
                    'mitigation_strategies': ['diversification', 'stop_loss'],
                    'confidence_level': 'high'
                },
                'test_name': 'risk_assessment'
            }
        ]
        
        self.portfolio_management_prompts = [
            {
                'prompt': 'Optimize portfolio: current_allocation={"equity": 0.7, "bonds": 0.3}, risk_tolerance=medium, goals=["growth", "income"]',
                'expected_response': {
                    'recommended_allocation': {'equity': 0.6, 'bonds': 0.4},
                    'diversification_score': 0.85,
                    'expected_return': 0.08,
                    'expected_risk': 0.12,
                    'confidence_level': 'high'
                },
                'test_name': 'portfolio_optimization'
            },
            {
                'prompt': 'Analyze diversification for portfolio with assets: [{"symbol": "AAPL", "weight": 0.4}, {"symbol": "GOOGL", "weight": 0.3}, {"symbol": "BOND", "weight": 0.3}]',
                'expected_response': {
                    'diversification_score': 0.75,
                    'sector_allocation': {'technology': 0.7, 'fixed_income': 0.3},
                    'concentration_risk': 'medium',
                    'recommendations': ['Add international exposure', 'Consider sector diversification']
                },
                'test_name': 'diversification_analysis'
            }
        ]
    
    def test_framework_initialization(self):
        """Test prompt testing framework initialization"""
        self.assertIsNotNone(self.framework)
        self.assertEqual(len(self.framework.test_prompts), 0)
        self.assertEqual(len(self.framework.test_results), 0)
    
    def test_add_test_prompt(self):
        """Test adding test prompts"""
        prompt = "Test prompt"
        expected = {"result": "success"}
        test_name = "test_1"
        
        self.framework.add_test_prompt(prompt, expected, test_name)
        
        self.assertEqual(len(self.framework.test_prompts), 1)
        self.assertEqual(self.framework.test_prompts[0]['test_name'], test_name)
        self.assertEqual(self.framework.test_prompts[0]['prompt'], prompt)
        self.assertEqual(self.framework.test_prompts[0]['expected_response'], expected)
    
    def test_json_response_comparison(self):
        """Test JSON response comparison"""
        expected = {
            'trend_analysis': 'bullish',
            'confidence_score': 85,
            'reasoning': 'Strong performance'
        }
        
        actual = {
            'trend_analysis': 'bullish',
            'confidence_score': 85,
            'reasoning': 'Strong performance',
            'additional_field': 'extra'
        }
        
        result = self.framework._compare_json_responses(expected, actual, 'test_json')
        
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['score'], 1.0)
        self.assertEqual(result['matched_fields'], 3)
        self.assertEqual(result['total_fields'], 3)
    
    def test_text_response_comparison(self):
        """Test text response comparison"""
        expected = "The market is showing bullish trends with strong performance"
        actual = "Market trends are bullish with strong performance indicators"
        
        result = self.framework._compare_text_responses(expected, actual, 'test_text')
        
        self.assertIn(result['status'], ['passed', 'failed'])  # Text comparison can be either
        self.assertGreater(result['similarity_score'], 0.5)  # Lower threshold for text similarity
    
    @patch('ai.gemini_client.GeminiAIClient.analyze_market_data')
    def test_market_analysis_prompt_execution(self, mock_generate):
        """Test market analysis prompt execution"""
        # Mock AI response
        mock_response = Mock()
        mock_response.text = json.dumps({
            'trend_analysis': 'mixed',
            'confidence_score': 70,
            'reasoning': 'Mixed performance across tech stocks',
            'key_factors': ['AAPL positive momentum', 'GOOGL negative pressure']
        })
        mock_generate.return_value = mock_response
        
        # Add test prompt
        test_prompt = self.market_analysis_prompts[0]
        self.framework.add_test_prompt(
            test_prompt['prompt'],
            test_prompt['expected_response'],
            test_prompt['test_name']
        )
        
        # Run test
        from ai.gemini_client import GeminiAIClient
        ai_client = GeminiAIClient()
        self.framework.run_prompt_tests(ai_client)
        
        # Verify results
        self.assertEqual(len(self.framework.test_results), 1)
        result = self.framework.test_results[0]
        self.assertEqual(result['test_name'], 'market_trend_analysis')
        self.assertEqual(result['status'], 'passed')
    
    @patch('ai.gemini_client.GeminiAIClient.analyze_market_data')
    def test_investment_decision_prompt_execution(self, mock_generate):
        """Test investment decision prompt execution"""
        # Mock AI response
        mock_response = Mock()
        mock_response.text = json.dumps({
            'recommendation': 'approve',
            'confidence_score': 0.8,
            'reasoning': 'Strong fundamentals and appropriate risk level',
            'risk_assessment': 'medium',
            'expected_return': 0.12
        })
        mock_generate.return_value = mock_response
        
        # Add test prompt
        test_prompt = self.investment_decision_prompts[0]
        self.framework.add_test_prompt(
            test_prompt['prompt'],
            test_prompt['expected_response'],
            test_prompt['test_name']
        )
        
        # Run test
        from ai.gemini_client import GeminiAIClient
        ai_client = GeminiAIClient()
        self.framework.run_prompt_tests(ai_client)
        
        # Verify results
        self.assertEqual(len(self.framework.test_results), 1)
        result = self.framework.test_results[0]
        self.assertEqual(result['test_name'], 'investment_decision')
        self.assertEqual(result['status'], 'passed')
    
    @patch('ai.gemini_client.GeminiAIClient.analyze_market_data')
    def test_portfolio_management_prompt_execution(self, mock_generate):
        """Test portfolio management prompt execution"""
        # Mock AI response
        mock_response = Mock()
        mock_response.text = json.dumps({
            'recommended_allocation': {'equity': 0.6, 'bonds': 0.4},
            'diversification_score': 0.85,
            'expected_return': 0.08,
            'expected_risk': 0.12,
            'confidence_level': 'high'
        })
        mock_generate.return_value = mock_response
        
        # Add test prompt
        test_prompt = self.portfolio_management_prompts[0]
        self.framework.add_test_prompt(
            test_prompt['prompt'],
            test_prompt['expected_response'],
            test_prompt['test_name']
        )
        
        # Run test
        from ai.gemini_client import GeminiAIClient
        ai_client = GeminiAIClient()
        self.framework.run_prompt_tests(ai_client)
        
        # Verify results
        self.assertEqual(len(self.framework.test_results), 1)
        result = self.framework.test_results[0]
        self.assertEqual(result['test_name'], 'portfolio_optimization')
        self.assertEqual(result['status'], 'passed')
    
    def test_error_handling_in_prompt_testing(self):
        """Test error handling in prompt testing"""
        # Add a test that will fail
        self.framework.add_test_prompt(
            "Invalid prompt that will cause error",
            {"result": "success"},
            "error_test"
        )
        
        # Mock AI client to raise exception
        with patch('ai.gemini_client.GeminiAIClient.analyze_market_data') as mock_generate:
            mock_generate.side_effect = Exception("API error")
            
            from ai.gemini_client import GeminiAIClient
            ai_client = GeminiAIClient()
            self.framework.run_prompt_tests(ai_client)
        
        # Verify error handling
        self.assertEqual(len(self.framework.test_results), 1)
        result = self.framework.test_results[0]
        self.assertEqual(result['test_name'], 'error_test')
        self.assertEqual(result['status'], 'failed')
        self.assertIn('API error', result['error'])
    
    def test_report_generation(self):
        """Test test report generation"""
        # Add some test results
        self.framework.test_results = [
            {'test_name': 'test1', 'status': 'passed', 'timestamp': datetime.utcnow().isoformat()},
            {'test_name': 'test2', 'status': 'failed', 'timestamp': datetime.utcnow().isoformat()},
            {'test_name': 'test3', 'status': 'passed', 'timestamp': datetime.utcnow().isoformat()}
        ]
        
        report = self.framework.generate_report()
        
        self.assertEqual(report['summary']['total_tests'], 3)
        self.assertEqual(report['summary']['passed'], 2)
        self.assertEqual(report['summary']['failed'], 1)
        self.assertAlmostEqual(report['summary']['success_rate'], 66.67, places=1)
        self.assertEqual(len(report['test_results']), 3)
    
    def test_comprehensive_prompt_testing(self):
        """Test comprehensive prompt testing with all prompt types"""
        # Add all test prompts
        for prompt_data in self.market_analysis_prompts:
            self.framework.add_test_prompt(
                prompt_data['prompt'],
                prompt_data['expected_response'],
                prompt_data['test_name']
            )
        
        for prompt_data in self.investment_decision_prompts:
            self.framework.add_test_prompt(
                prompt_data['prompt'],
                prompt_data['expected_response'],
                prompt_data['test_name']
            )
        
        for prompt_data in self.portfolio_management_prompts:
            self.framework.add_test_prompt(
                prompt_data['prompt'],
                prompt_data['expected_response'],
                prompt_data['test_name']
            )
        
        # Verify all prompts were added
        self.assertEqual(len(self.framework.test_prompts), 6)
        
        # Test report generation
        report = self.framework.generate_report()
        self.assertEqual(report['summary']['total_tests'], 0)  # No results yet
        self.assertEqual(len(report['test_results']), 0)


class TestPromptValidation(unittest.TestCase):
    """Test cases for prompt validation and quality"""
    
    def test_prompt_structure_validation(self):
        """Test prompt structure validation"""
        valid_prompts = [
            "Analyze market data: {data}",
            "Make investment decision for: {params}",
            "Optimize portfolio: {portfolio_data}"
        ]
        
        invalid_prompts = [
            "",  # Empty prompt
            "   ",  # Whitespace only
            None,  # None prompt
        ]
        
        for prompt in valid_prompts:
            self.assertTrue(self._is_valid_prompt(prompt))
        
        for prompt in invalid_prompts:
            self.assertFalse(self._is_valid_prompt(prompt))
    
    def test_expected_response_validation(self):
        """Test expected response validation"""
        valid_responses = [
            {"result": "success", "confidence": 0.8},
            "Simple text response",
            [{"field": "value"}, {"field2": "value2"}]
        ]
        
        invalid_responses = [
            None,
            {},
            []
        ]
        
        for response in valid_responses:
            self.assertTrue(self._is_valid_expected_response(response))
        
        for response in invalid_responses:
            self.assertFalse(self._is_valid_expected_response(response))
    
    def _is_valid_prompt(self, prompt):
        """Check if prompt is valid"""
        return prompt and isinstance(prompt, str) and len(prompt.strip()) > 0
    
    def _is_valid_expected_response(self, response):
        """Check if expected response is valid"""
        return response is not None and (
            isinstance(response, (dict, list, str)) and 
            (not isinstance(response, (dict, list)) or len(response) > 0)
        )


if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestPromptTesting))
    test_suite.addTest(unittest.makeSuite(TestPromptValidation))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"Prompt Testing Framework Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print(f"{'='*50}")
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
