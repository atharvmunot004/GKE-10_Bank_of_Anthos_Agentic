#!/usr/bin/env python3
# Copyright 2024 Google LLC
# Bank Asset Agent - Rule Validator

import requests
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class RuleValidator:
    """AI agent for investment rule validation and compliance checking"""
    
    def __init__(self, rule_checker_url: str = None):
        self.rule_checker_url = rule_checker_url or os.environ.get('RULE_CHECKER_URL', 'http://rule-checker-svc:8080')
    
    def validate_investment_rules(self, investment_data: Dict) -> Dict:
        """Validate investment rules and compliance"""
        try:
            response = requests.post(
                f"{self.rule_checker_url}/api/validate",
                json=investment_data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to validate investment rules: {e}")
            raise Exception(f"Rule validation failed: {e}")
    
    def assess_risk(self, investment_data: Dict) -> Dict:
        """Assess investment risk level"""
        try:
            risk_factors = self._calculate_risk_factors(investment_data)
            risk_score = self._calculate_risk_score(risk_factors)
            risk_level = self._determine_risk_level(risk_score)
            
            return {
                'risk_score': risk_score,
                'risk_level': risk_level,
                'risk_factors': risk_factors,
                'recommendations': self._get_risk_recommendations(risk_level),
                'assessment_timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to assess risk: {e}")
            raise Exception(f"Risk assessment failed: {e}")
    
    def validate_compliance(self, investment_data: Dict, user_context: Dict) -> Dict:
        """Validate compliance requirements"""
        try:
            compliance_checks = {
                'kyc_status': self._check_kyc_status(user_context),
                'aml_check': self._check_aml_compliance(investment_data, user_context),
                'regulatory_limits': self._check_regulatory_limits(investment_data, user_context),
                'investment_limits': self._check_investment_limits(investment_data, user_context)
            }
            
            overall_compliance = all(compliance_checks.values())
            
            return {
                'compliant': overall_compliance,
                'compliance_checks': compliance_checks,
                'compliance_timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to validate compliance: {e}")
            raise Exception(f"Compliance validation failed: {e}")
    
    def check_investment_rules(self, investment_data: Dict) -> Dict:
        """Check specific investment rules"""
        try:
            rules = {
                'minimum_investment': self._check_minimum_investment(investment_data),
                'maximum_investment': self._check_maximum_investment(investment_data),
                'asset_availability': self._check_asset_availability(investment_data),
                'user_eligibility': self._check_user_eligibility(investment_data),
                'market_hours': self._check_market_hours(investment_data)
            }
            
            all_rules_passed = all(rules.values())
            
            return {
                'rules_passed': all_rules_passed,
                'rule_checks': rules,
                'validation_timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to check investment rules: {e}")
            raise Exception(f"Investment rules check failed: {e}")
    
    def _calculate_risk_factors(self, investment_data: Dict) -> Dict:
        """Calculate various risk factors"""
        amount = investment_data.get('amount', 0)
        asset_symbol = investment_data.get('asset_symbol', '')
        investment_type = investment_data.get('investment_type', 'buy')
        
        return {
            'amount_risk': min(1.0, amount / 100000),  # Higher amount = higher risk
            'asset_volatility': self._get_asset_volatility(asset_symbol),
            'market_risk': self._get_market_risk(),
            'liquidity_risk': self._get_liquidity_risk(asset_symbol),
            'concentration_risk': self._get_concentration_risk(investment_data)
        }
    
    def _calculate_risk_score(self, risk_factors: Dict) -> float:
        """Calculate overall risk score"""
        weights = {
            'amount_risk': 0.3,
            'asset_volatility': 0.25,
            'market_risk': 0.2,
            'liquidity_risk': 0.15,
            'concentration_risk': 0.1
        }
        
        return sum(risk_factors[factor] * weights[factor] for factor in risk_factors)
    
    def _determine_risk_level(self, risk_score: float) -> str:
        """Determine risk level based on score"""
        if risk_score < 0.3:
            return "low"
        elif risk_score < 0.6:
            return "medium"
        else:
            return "high"
    
    def _get_risk_recommendations(self, risk_level: str) -> List[str]:
        """Get risk-based recommendations"""
        recommendations = {
            "low": ["Proceed with investment", "Consider diversifying portfolio"],
            "medium": ["Monitor market conditions", "Consider smaller position size"],
            "high": ["Review investment strategy", "Consider risk mitigation", "Consult financial advisor"]
        }
        return recommendations.get(risk_level, ["Review investment carefully"])
    
    def _check_kyc_status(self, user_context: Dict) -> bool:
        """Check KYC status"""
        return user_context.get('kyc_verified', False)
    
    def _check_aml_compliance(self, investment_data: Dict, user_context: Dict) -> bool:
        """Check AML compliance"""
        amount = investment_data.get('amount', 0)
        return amount < 10000 or user_context.get('aml_verified', False)
    
    def _check_regulatory_limits(self, investment_data: Dict, user_context: Dict) -> bool:
        """Check regulatory limits"""
        # Simplified regulatory checks
        return True
    
    def _check_investment_limits(self, investment_data: Dict, user_context: Dict) -> bool:
        """Check investment limits"""
        amount = investment_data.get('amount', 0)
        user_limit = user_context.get('investment_limit', 50000)
        return amount <= user_limit
    
    def _check_minimum_investment(self, investment_data: Dict) -> bool:
        """Check minimum investment amount"""
        amount = investment_data.get('amount', 0)
        return amount >= 100  # Minimum $100 investment
    
    def _check_maximum_investment(self, investment_data: Dict) -> bool:
        """Check maximum investment amount"""
        amount = investment_data.get('amount', 0)
        return amount <= 1000000  # Maximum $1M investment
    
    def _check_asset_availability(self, investment_data: Dict) -> bool:
        """Check asset availability"""
        # Simplified availability check
        return True
    
    def _check_user_eligibility(self, investment_data: Dict) -> bool:
        """Check user eligibility"""
        # Simplified eligibility check
        return True
    
    def _check_market_hours(self, investment_data: Dict) -> bool:
        """Check if market is open"""
        # Simplified market hours check
        return True
    
    def _get_asset_volatility(self, asset_symbol: str) -> float:
        """Get asset volatility (simplified)"""
        # Simplified volatility calculation
        volatility_map = {
            'AAPL': 0.3,
            'GOOGL': 0.4,
            'MSFT': 0.25,
            'TSLA': 0.8
        }
        return volatility_map.get(asset_symbol, 0.5)
    
    def _get_market_risk(self) -> float:
        """Get current market risk"""
        # Simplified market risk calculation
        return 0.4
    
    def _get_liquidity_risk(self, asset_symbol: str) -> float:
        """Get liquidity risk for asset"""
        # Simplified liquidity risk calculation
        return 0.2
    
    def _get_concentration_risk(self, investment_data: Dict) -> float:
        """Get concentration risk"""
        # Simplified concentration risk calculation
        return 0.3
