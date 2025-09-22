#!/usr/bin/env python3
# Copyright 2024 Google LLC
# Bank Asset Agent - AI Decision Making Tools

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from ai.gemini_client import GeminiAIClient

logger = logging.getLogger(__name__)

class AIDecisionMaker:
    """AI-powered investment decision making using Gemini AI"""
    
    def __init__(self, gemini_client: GeminiAIClient = None):
        """Initialize AI decision maker"""
        self.gemini_client = gemini_client or GeminiAIClient()
        self.decision_cache = {}
        self.cache_ttl = 600  # 10 minutes cache TTL
    
    def make_investment_decision(self, investment_request: Dict[str, Any],
                                market_data: Dict[str, Any],
                                user_profile: Dict[str, Any],
                                risk_rules: Dict[str, Any]) -> Dict[str, Any]:
        """Make AI-powered investment decision"""
        try:
            # Check cache first
            cache_key = self._generate_cache_key(investment_request, market_data, user_profile)
            if self._is_cache_valid(cache_key):
                logger.info("Returning cached investment decision")
                return self.decision_cache[cache_key]
            
            # Perform AI decision making
            decision = self.gemini_client.make_investment_decision(
                investment_request=investment_request,
                market_data=market_data,
                user_profile=user_profile,
                risk_rules=risk_rules
            )
            
            # Add decision metadata
            decision['decision_timestamp'] = datetime.utcnow().isoformat()
            decision['decision_id'] = self._generate_decision_id()
            decision['cache_key'] = cache_key
            
            # Cache the decision
            self.decision_cache[cache_key] = decision
            
            logger.info(f"Investment decision made: {decision.get('recommendation', 'Unknown')}")
            return decision
            
        except Exception as e:
            logger.error(f"Investment decision making failed: {e}")
            return self._create_error_response("Investment decision failed", str(e))
    
    def assess_investment_risk(self, investment_details: Dict[str, Any],
                              market_conditions: Dict[str, Any],
                              user_risk_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Assess investment risk using AI"""
        try:
            # Prepare risk assessment context
            risk_context = {
                'investment_details': investment_details,
                'market_conditions': market_conditions,
                'user_risk_profile': user_risk_profile,
                'assessment_type': 'investment_risk'
            }
            
            # Perform AI risk analysis
            risk_analysis = self.gemini_client.analyze_risk(
                investment_details=investment_details,
                market_volatility=market_conditions.get('volatility', {}),
                economic_indicators=market_conditions.get('economic_indicators', {}),
                historical_performance=investment_details.get('historical_performance', {})
            )
            
            # Add risk assessment metadata
            risk_analysis['assessment_timestamp'] = datetime.utcnow().isoformat()
            risk_analysis['assessment_id'] = self._generate_assessment_id()
            
            logger.info(f"Risk assessment completed: {risk_analysis.get('overall_risk_score', 0)}% risk")
            return risk_analysis
            
        except Exception as e:
            logger.error(f"Risk assessment failed: {e}")
            return self._create_error_response("Risk assessment failed", str(e))
    
    def validate_compliance(self, investment_request: Dict[str, Any],
                           regulatory_rules: Dict[str, Any],
                           user_compliance_status: Dict[str, Any]) -> Dict[str, Any]:
        """Validate compliance using AI"""
        try:
            # Prepare compliance validation context
            compliance_context = {
                'investment_request': investment_request,
                'regulatory_rules': regulatory_rules,
                'user_compliance_status': user_compliance_status,
                'validation_type': 'compliance'
            }
            
            # Generate AI insights for compliance
            ai_insights = self.gemini_client.generate_investment_insights(compliance_context)
            
            # Create compliance validation result
            compliance_result = {
                'compliant': self._determine_compliance_status(ai_insights, regulatory_rules),
                'violations': self._identify_violations(ai_insights, regulatory_rules),
                'recommendations': ai_insights.get('strategic_recommendations', []),
                'confidence_score': self._calculate_compliance_confidence(ai_insights),
                'validation_timestamp': datetime.utcnow().isoformat(),
                'ai_reasoning': ai_insights.get('reasoning', ''),
                'regulatory_checks': self._perform_regulatory_checks(investment_request, regulatory_rules)
            }
            
            logger.info(f"Compliance validation completed: {compliance_result['compliant']}")
            return compliance_result
            
        except Exception as e:
            logger.error(f"Compliance validation failed: {e}")
            return self._create_error_response("Compliance validation failed", str(e))
    
    def generate_alternative_strategies(self, original_request: Dict[str, Any],
                                      market_conditions: Dict[str, Any],
                                      user_preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Generate alternative investment strategies using AI"""
        try:
            # Prepare strategy generation context
            strategy_context = {
                'original_request': original_request,
                'market_conditions': market_conditions,
                'user_preferences': user_preferences,
                'strategy_type': 'alternatives'
            }
            
            # Generate AI insights for strategies
            ai_insights = self.gemini_client.generate_investment_insights(strategy_context)
            
            # Create alternative strategies
            strategies = self._create_alternative_strategies(
                original_request, market_conditions, user_preferences, ai_insights
            )
            
            result = {
                'alternative_strategies': strategies,
                'original_analysis': ai_insights,
                'strategy_timestamp': datetime.utcnow().isoformat(),
                'confidence_level': ai_insights.get('confidence_level', 'medium'),
                'reasoning': ai_insights.get('reasoning', '')
            }
            
            logger.info(f"Alternative strategies generated: {len(strategies)} strategies")
            return result
            
        except Exception as e:
            logger.error(f"Alternative strategy generation failed: {e}")
            return self._create_error_response("Alternative strategy generation failed", str(e))
    
    def evaluate_investment_opportunity(self, opportunity_data: Dict[str, Any],
                                      market_analysis: Dict[str, Any],
                                      portfolio_context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate investment opportunity using AI"""
        try:
            # Prepare evaluation context
            evaluation_context = {
                'opportunity_data': opportunity_data,
                'market_analysis': market_analysis,
                'portfolio_context': portfolio_context,
                'evaluation_type': 'opportunity'
            }
            
            # Generate AI insights for evaluation
            ai_insights = self.gemini_client.generate_investment_insights(evaluation_context)
            
            # Create opportunity evaluation
            evaluation = {
                'opportunity_score': self._calculate_opportunity_score(ai_insights, opportunity_data),
                'risk_reward_ratio': self._calculate_risk_reward_ratio(opportunity_data, market_analysis),
                'portfolio_fit': self._assess_portfolio_fit(opportunity_data, portfolio_context),
                'market_timing': self._assess_market_timing(opportunity_data, market_analysis),
                'recommendation': self._generate_opportunity_recommendation(ai_insights),
                'key_factors': ai_insights.get('key_metrics', []),
                'evaluation_timestamp': datetime.utcnow().isoformat(),
                'ai_reasoning': ai_insights.get('reasoning', '')
            }
            
            logger.info(f"Investment opportunity evaluated: {evaluation['opportunity_score']} score")
            return evaluation
            
        except Exception as e:
            logger.error(f"Investment opportunity evaluation failed: {e}")
            return self._create_error_response("Investment opportunity evaluation failed", str(e))
    
    def _determine_compliance_status(self, ai_insights: Dict[str, Any], 
                                   regulatory_rules: Dict[str, Any]) -> bool:
        """Determine compliance status based on AI insights and rules"""
        # Simplified compliance logic - in practice, this would be more sophisticated
        confidence = ai_insights.get('confidence_level', 'medium')
        recommendations = ai_insights.get('strategic_recommendations', [])
        
        # Check for compliance violations in recommendations
        violation_keywords = ['violation', 'non-compliant', 'breach', 'illegal']
        has_violations = any(
            any(keyword in rec.lower() for keyword in violation_keywords)
            for rec in recommendations
        )
        
        return not has_violations and confidence in ['high', 'medium']
    
    def _identify_violations(self, ai_insights: Dict[str, Any], 
                           regulatory_rules: Dict[str, Any]) -> List[str]:
        """Identify specific compliance violations"""
        violations = []
        recommendations = ai_insights.get('strategic_recommendations', [])
        
        # Check for specific violation patterns
        for rec in recommendations:
            if any(keyword in rec.lower() for keyword in ['violation', 'non-compliant', 'breach']):
                violations.append(rec)
        
        return violations
    
    def _calculate_compliance_confidence(self, ai_insights: Dict[str, Any]) -> float:
        """Calculate confidence score for compliance validation"""
        confidence_level = ai_insights.get('confidence_level', 'medium')
        confidence_map = {'high': 0.9, 'medium': 0.7, 'low': 0.5}
        return confidence_map.get(confidence_level, 0.7)
    
    def _perform_regulatory_checks(self, investment_request: Dict[str, Any],
                                 regulatory_rules: Dict[str, Any]) -> Dict[str, Any]:
        """Perform specific regulatory checks"""
        checks = {
            'amount_limits': self._check_amount_limits(investment_request, regulatory_rules),
            'asset_restrictions': self._check_asset_restrictions(investment_request, regulatory_rules),
            'user_eligibility': self._check_user_eligibility(investment_request, regulatory_rules),
            'timing_restrictions': self._check_timing_restrictions(investment_request, regulatory_rules)
        }
        
        return checks
    
    def _check_amount_limits(self, request: Dict[str, Any], rules: Dict[str, Any]) -> bool:
        """Check investment amount against limits"""
        amount = request.get('amount', 0)
        max_amount = rules.get('max_investment_amount', float('inf'))
        return amount <= max_amount
    
    def _check_asset_restrictions(self, request: Dict[str, Any], rules: Dict[str, Any]) -> bool:
        """Check asset against restrictions"""
        asset_symbol = request.get('asset_symbol', '')
        restricted_assets = rules.get('restricted_assets', [])
        return asset_symbol not in restricted_assets
    
    def _check_user_eligibility(self, request: Dict[str, Any], rules: Dict[str, Any]) -> bool:
        """Check user eligibility for investment"""
        user_tier = request.get('user_tier', 1)
        min_tier = rules.get('min_user_tier', 1)
        return user_tier >= min_tier
    
    def _check_timing_restrictions(self, request: Dict[str, Any], rules: Dict[str, Any]) -> bool:
        """Check timing restrictions"""
        # Simplified timing check - in practice, this would check market hours, etc.
        return True
    
    def _create_alternative_strategies(self, original_request: Dict[str, Any],
                                     market_conditions: Dict[str, Any],
                                     user_preferences: Dict[str, Any],
                                     ai_insights: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create alternative investment strategies"""
        strategies = []
        
        # Strategy 1: Conservative approach
        strategies.append({
            'strategy_name': 'Conservative Alternative',
            'description': 'Lower risk, stable returns approach',
            'asset_allocation': {'bonds': 0.7, 'stocks': 0.3},
            'expected_returns': 0.05,
            'risk_level': 'low',
            'reasoning': 'Focus on capital preservation with steady growth'
        })
        
        # Strategy 2: Aggressive approach
        strategies.append({
            'strategy_name': 'Growth Alternative',
            'description': 'Higher risk, higher potential returns',
            'asset_allocation': {'stocks': 0.8, 'bonds': 0.2},
            'expected_returns': 0.12,
            'risk_level': 'high',
            'reasoning': 'Focus on capital growth with higher volatility'
        })
        
        # Strategy 3: Balanced approach
        strategies.append({
            'strategy_name': 'Balanced Alternative',
            'description': 'Moderate risk, balanced returns',
            'asset_allocation': {'stocks': 0.6, 'bonds': 0.4},
            'expected_returns': 0.08,
            'risk_level': 'medium',
            'reasoning': 'Balance between growth and stability'
        })
        
        return strategies
    
    def _calculate_opportunity_score(self, ai_insights: Dict[str, Any], 
                                   opportunity_data: Dict[str, Any]) -> float:
        """Calculate opportunity score based on AI insights"""
        # Simplified scoring - in practice, this would be more sophisticated
        confidence = ai_insights.get('confidence_level', 'medium')
        confidence_scores = {'high': 0.9, 'medium': 0.7, 'low': 0.5}
        base_score = confidence_scores.get(confidence, 0.7)
        
        # Adjust based on opportunity data
        amount = opportunity_data.get('amount', 0)
        if amount > 10000:  # Large investment
            base_score += 0.1
        elif amount < 1000:  # Small investment
            base_score -= 0.1
        
        return min(max(base_score, 0.0), 1.0)
    
    def _calculate_risk_reward_ratio(self, opportunity_data: Dict[str, Any],
                                   market_analysis: Dict[str, Any]) -> float:
        """Calculate risk-reward ratio"""
        # Simplified calculation
        expected_return = opportunity_data.get('expected_return', 0.08)
        risk_level = market_analysis.get('volatility', 0.15)
        return expected_return / risk_level if risk_level > 0 else 0
    
    def _assess_portfolio_fit(self, opportunity_data: Dict[str, Any],
                            portfolio_context: Dict[str, Any]) -> str:
        """Assess how well the opportunity fits the portfolio"""
        # Simplified assessment
        portfolio_diversification = portfolio_context.get('diversification_score', 0.5)
        if portfolio_diversification < 0.3:
            return 'excellent'  # Portfolio needs diversification
        elif portfolio_diversification < 0.6:
            return 'good'
        else:
            return 'moderate'
    
    def _assess_market_timing(self, opportunity_data: Dict[str, Any],
                            market_analysis: Dict[str, Any]) -> str:
        """Assess market timing for the opportunity"""
        # Simplified assessment
        market_sentiment = market_analysis.get('sentiment', 'neutral')
        if market_sentiment == 'bullish':
            return 'excellent'
        elif market_sentiment == 'neutral':
            return 'good'
        else:
            return 'poor'
    
    def _generate_opportunity_recommendation(self, ai_insights: Dict[str, Any]) -> str:
        """Generate opportunity recommendation"""
        confidence = ai_insights.get('confidence_level', 'medium')
        if confidence == 'high':
            return 'strong_buy'
        elif confidence == 'medium':
            return 'buy'
        else:
            return 'hold'
    
    def _generate_cache_key(self, *args) -> str:
        """Generate cache key for arguments"""
        import hashlib
        data_str = json.dumps(args, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is valid"""
        if cache_key not in self.decision_cache:
            return False
        
        cached_at = datetime.fromisoformat(self.decision_cache[cache_key]['decision_timestamp'])
        return (datetime.utcnow() - cached_at).total_seconds() < self.cache_ttl
    
    def _generate_decision_id(self) -> str:
        """Generate unique decision ID"""
        return f"decision_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{hash(str(datetime.utcnow())) % 10000}"
    
    def _generate_assessment_id(self) -> str:
        """Generate unique assessment ID"""
        return f"assessment_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{hash(str(datetime.utcnow())) % 10000}"
    
    def _create_error_response(self, error_type: str, error_message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            'error': True,
            'error_type': error_type,
            'error_message': error_message,
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'ai_decision_maker'
        }
