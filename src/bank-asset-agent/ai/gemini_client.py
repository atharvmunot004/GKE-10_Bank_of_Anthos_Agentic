#!/usr/bin/env python3
# Copyright 2024 Google LLC
# Bank Asset Agent - Gemini AI Integration

import google.generativeai as genai
import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class GeminiAIClient:
    """Google Gemini AI client for investment analysis and decision making"""
    
    def __init__(self, api_key: str = None):
        """Initialize Gemini AI client"""
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("Gemini API key not provided. Set GEMINI_API_KEY environment variable.")
        
        # Configure Gemini AI
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Investment analysis prompts
        self.investment_prompts = {
            'market_analysis': """
            Analyze the following market data and provide investment insights:
            
            Market Data: {market_data}
            
            Please provide:
            1. Market trend analysis (bullish/bearish/neutral)
            2. Risk assessment (low/medium/high)
            3. Investment recommendations
            4. Key factors influencing the market
            5. Confidence score (0-100)
            
            Format your response as JSON with the following structure:
            {{
                "trend_analysis": "string",
                "risk_level": "string",
                "recommendations": ["string"],
                "key_factors": ["string"],
                "confidence_score": number,
                "reasoning": "string"
            }}
            """,
            
            'portfolio_optimization': """
            Optimize the following investment portfolio based on market conditions:
            
            Current Portfolio: {portfolio_data}
            Market Conditions: {market_conditions}
            Risk Tolerance: {risk_tolerance}
            Investment Goals: {investment_goals}
            
            Please provide:
            1. Recommended asset allocation changes
            2. Risk assessment of current portfolio
            3. Expected returns and volatility
            4. Rebalancing recommendations
            5. Diversification analysis
            
            Format your response as JSON with the following structure:
            {{
                "recommended_allocation": {{"asset1": percentage, "asset2": percentage}},
                "risk_assessment": "string",
                "expected_returns": number,
                "expected_volatility": number,
                "rebalancing_actions": ["string"],
                "diversification_score": number,
                "reasoning": "string"
            }}
            """,
            
            'investment_decision': """
            Make an investment decision based on the following parameters:
            
            Investment Request: {investment_request}
            Market Data: {market_data}
            User Profile: {user_profile}
            Risk Rules: {risk_rules}
            
            Please provide:
            1. Investment recommendation (approve/deny/modify)
            2. Risk assessment
            3. Expected returns
            4. Alternative suggestions
            5. Reasoning for the decision
            
            Format your response as JSON with the following structure:
            {{
                "recommendation": "approve|deny|modify",
                "risk_assessment": "string",
                "expected_returns": number,
                "alternative_suggestions": ["string"],
                "reasoning": "string",
                "confidence_score": number,
                "conditions": ["string"]
            }}
            """,
            
            'risk_analysis': """
            Analyze the risk profile for the following investment:
            
            Investment Details: {investment_details}
            Market Volatility: {market_volatility}
            Economic Indicators: {economic_indicators}
            Historical Performance: {historical_performance}
            
            Please provide:
            1. Overall risk score (0-100)
            2. Risk factors and their impact
            3. Mitigation strategies
            4. Stress test scenarios
            5. Risk-adjusted return expectations
            
            Format your response as JSON with the following structure:
            {{
                "overall_risk_score": number,
                "risk_factors": [{{"factor": "string", "impact": "high|medium|low", "description": "string"}}],
                "mitigation_strategies": ["string"],
                "stress_test_scenarios": [{{"scenario": "string", "impact": "string"}}],
                "risk_adjusted_returns": number,
                "recommendations": ["string"]
            }}
            """
        }
    
    def analyze_market_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market data using Gemini AI"""
        try:
            prompt = self.investment_prompts['market_analysis'].format(
                market_data=json.dumps(market_data, indent=2)
            )
            
            response = self.model.generate_content(prompt)
            
            # Parse JSON response
            analysis = json.loads(response.text)
            
            # Add metadata
            analysis['timestamp'] = datetime.utcnow().isoformat()
            analysis['model'] = 'gemini-1.5-pro'
            analysis['source'] = 'gemini_ai'
            
            logger.info(f"Market analysis completed: {analysis.get('trend_analysis', 'Unknown')}")
            return analysis
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            return self._create_error_response("JSON parsing failed", str(e))
        except Exception as e:
            logger.error(f"Market analysis failed: {e}")
            return self._create_error_response("Market analysis failed", str(e))
    
    def optimize_portfolio(self, portfolio_data: Dict[str, Any], 
                          market_conditions: Dict[str, Any],
                          risk_tolerance: str = "medium",
                          investment_goals: List[str] = None) -> Dict[str, Any]:
        """Optimize portfolio using Gemini AI"""
        try:
            prompt = self.investment_prompts['portfolio_optimization'].format(
                portfolio_data=json.dumps(portfolio_data, indent=2),
                market_conditions=json.dumps(market_conditions, indent=2),
                risk_tolerance=risk_tolerance,
                investment_goals=json.dumps(investment_goals or [], indent=2)
            )
            
            response = self.model.generate_content(prompt)
            
            # Parse JSON response
            optimization = json.loads(response.text)
            
            # Add metadata
            optimization['timestamp'] = datetime.utcnow().isoformat()
            optimization['model'] = 'gemini-1.5-pro'
            optimization['source'] = 'gemini_ai'
            
            logger.info(f"Portfolio optimization completed: {optimization.get('diversification_score', 0)}% diversification")
            return optimization
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            return self._create_error_response("JSON parsing failed", str(e))
        except Exception as e:
            logger.error(f"Portfolio optimization failed: {e}")
            return self._create_error_response("Portfolio optimization failed", str(e))
    
    def make_investment_decision(self, investment_request: Dict[str, Any],
                                market_data: Dict[str, Any],
                                user_profile: Dict[str, Any],
                                risk_rules: Dict[str, Any]) -> Dict[str, Any]:
        """Make investment decision using Gemini AI"""
        try:
            prompt = self.investment_prompts['investment_decision'].format(
                investment_request=json.dumps(investment_request, indent=2),
                market_data=json.dumps(market_data, indent=2),
                user_profile=json.dumps(user_profile, indent=2),
                risk_rules=json.dumps(risk_rules, indent=2)
            )
            
            response = self.model.generate_content(prompt)
            
            # Parse JSON response
            decision = json.loads(response.text)
            
            # Add metadata
            decision['timestamp'] = datetime.utcnow().isoformat()
            decision['model'] = 'gemini-1.5-pro'
            decision['source'] = 'gemini_ai'
            
            logger.info(f"Investment decision made: {decision.get('recommendation', 'Unknown')}")
            return decision
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            return self._create_error_response("JSON parsing failed", str(e))
        except Exception as e:
            logger.error(f"Investment decision failed: {e}")
            return self._create_error_response("Investment decision failed", str(e))
    
    def analyze_risk(self, investment_details: Dict[str, Any],
                    market_volatility: Dict[str, Any],
                    economic_indicators: Dict[str, Any],
                    historical_performance: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze investment risk using Gemini AI"""
        try:
            prompt = self.investment_prompts['risk_analysis'].format(
                investment_details=json.dumps(investment_details, indent=2),
                market_volatility=json.dumps(market_volatility, indent=2),
                economic_indicators=json.dumps(economic_indicators, indent=2),
                historical_performance=json.dumps(historical_performance, indent=2)
            )
            
            response = self.model.generate_content(prompt)
            
            # Parse JSON response
            risk_analysis = json.loads(response.text)
            
            # Add metadata
            risk_analysis['timestamp'] = datetime.utcnow().isoformat()
            risk_analysis['model'] = 'gemini-1.5-pro'
            risk_analysis['source'] = 'gemini_ai'
            
            logger.info(f"Risk analysis completed: {risk_analysis.get('overall_risk_score', 0)}% risk score")
            return risk_analysis
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            return self._create_error_response("JSON parsing failed", str(e))
        except Exception as e:
            logger.error(f"Risk analysis failed: {e}")
            return self._create_error_response("Risk analysis failed", str(e))
    
    def generate_investment_insights(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate general investment insights using Gemini AI"""
        try:
            prompt = f"""
            As an expert investment advisor, provide insights based on the following context:
            
            Context: {json.dumps(context, indent=2)}
            
            Please provide:
            1. Market outlook and trends
            2. Investment opportunities
            3. Risk considerations
            4. Strategic recommendations
            5. Key metrics to watch
            
            Format your response as JSON with the following structure:
            {{
                "market_outlook": "string",
                "investment_opportunities": ["string"],
                "risk_considerations": ["string"],
                "strategic_recommendations": ["string"],
                "key_metrics": ["string"],
                "confidence_level": "high|medium|low",
                "reasoning": "string"
            }}
            """
            
            response = self.model.generate_content(prompt)
            
            # Parse JSON response
            insights = json.loads(response.text)
            
            # Add metadata
            insights['timestamp'] = datetime.utcnow().isoformat()
            insights['model'] = 'gemini-1.5-pro'
            insights['source'] = 'gemini_ai'
            
            logger.info(f"Investment insights generated: {insights.get('confidence_level', 'Unknown')} confidence")
            return insights
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            return self._create_error_response("JSON parsing failed", str(e))
        except Exception as e:
            logger.error(f"Investment insights generation failed: {e}")
            return self._create_error_response("Investment insights generation failed", str(e))
    
    def _create_error_response(self, error_type: str, error_message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            'error': True,
            'error_type': error_type,
            'error_message': error_message,
            'timestamp': datetime.utcnow().isoformat(),
            'model': 'gemini-1.5-pro',
            'source': 'gemini_ai'
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Check Gemini AI service health"""
        try:
            # Simple test prompt
            test_prompt = "Respond with 'OK' if you can process this request."
            response = self.model.generate_content(test_prompt)
            
            return {
                'status': 'healthy',
                'model': 'gemini-1.5-pro',
                'response_time': '< 1s',
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Gemini AI health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

def create_gemini_client(api_key: str = None) -> GeminiAIClient:
    """Factory function to create Gemini AI client"""
    return GeminiAIClient(api_key)
