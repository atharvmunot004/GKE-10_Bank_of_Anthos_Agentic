#!/usr/bin/env python3
# Copyright 2024 Google LLC
# Bank Asset Agent - Data Models

from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

class InvestmentType(Enum):
    """Investment type enumeration"""
    BUY = "buy"
    SELL = "sell"

class OrderStatus(Enum):
    """Order status enumeration"""
    PENDING = "pending"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    FAILED = "failed"

class RiskLevel(Enum):
    """Risk level enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class TrendType(Enum):
    """Trend type enumeration"""
    STRONG_BULLISH = "strong_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    STRONG_BEARISH = "strong_bearish"

@dataclass
class AssetInfo:
    """Asset information model"""
    asset_id: str
    tier_number: int
    asset_name: str
    amount: float
    price_per_unit: float
    last_updated: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'asset_id': self.asset_id,
            'tier_number': self.tier_number,
            'asset_name': self.asset_name,
            'amount': self.amount,
            'price_per_unit': self.price_per_unit,
            'last_updated': self.last_updated.isoformat()
        }

@dataclass
class MarketData:
    """Market data model"""
    symbol: str
    price: float
    change: float
    change_percent: float
    volume: int
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'price': self.price,
            'change': self.change,
            'change_percent': self.change_percent,
            'volume': self.volume,
            'timestamp': self.timestamp.isoformat()
        }

@dataclass
class TrendAnalysis:
    """Trend analysis model"""
    symbol: str
    trend: TrendType
    confidence: float
    price: float
    change: float
    change_percent: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'trend': self.trend.value,
            'confidence': self.confidence,
            'price': self.price,
            'change': self.change,
            'change_percent': self.change_percent
        }

@dataclass
class PricePrediction:
    """Price prediction model"""
    symbol: str
    current_price: float
    predicted_price: float
    predicted_change: float
    confidence: float
    trend: TrendType
    horizon: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'current_price': self.current_price,
            'predicted_price': self.predicted_price,
            'predicted_change': self.predicted_change,
            'confidence': self.confidence,
            'trend': self.trend.value,
            'horizon': self.horizon
        }

@dataclass
class InvestmentRequest:
    """Investment request model"""
    user_id: str
    asset_symbol: str
    amount: float
    quantity: float
    investment_type: InvestmentType
    price: Optional[float] = None
    timestamp: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'asset_symbol': self.asset_symbol,
            'amount': self.amount,
            'quantity': self.quantity,
            'investment_type': self.investment_type.value,
            'price': self.price,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

@dataclass
class OrderResult:
    """Order execution result model"""
    order_id: str
    status: OrderStatus
    user_id: str
    asset_symbol: str
    quantity: float
    executed_price: float
    total_cost: float
    fees: float
    timestamp: datetime
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'order_id': self.order_id,
            'status': self.status.value,
            'user_id': self.user_id,
            'asset_symbol': self.asset_symbol,
            'quantity': self.quantity,
            'executed_price': self.executed_price,
            'total_cost': self.total_cost,
            'fees': self.fees,
            'timestamp': self.timestamp.isoformat(),
            'error_message': self.error_message
        }

@dataclass
class RiskAssessment:
    """Risk assessment model"""
    risk_score: float
    risk_level: RiskLevel
    risk_factors: Dict[str, float]
    recommendations: List[str]
    assessment_timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'risk_score': self.risk_score,
            'risk_level': self.risk_level.value,
            'risk_factors': self.risk_factors,
            'recommendations': self.recommendations,
            'assessment_timestamp': self.assessment_timestamp.isoformat()
        }

@dataclass
class RuleValidation:
    """Rule validation model"""
    rules_passed: bool
    rule_checks: Dict[str, bool]
    validation_timestamp: datetime
    errors: List[str] = None
    warnings: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'rules_passed': self.rules_passed,
            'rule_checks': self.rule_checks,
            'validation_timestamp': self.validation_timestamp.isoformat(),
            'errors': self.errors or [],
            'warnings': self.warnings or []
        }

@dataclass
class ComplianceValidation:
    """Compliance validation model"""
    compliant: bool
    compliance_checks: Dict[str, bool]
    compliance_timestamp: datetime
    violations: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'compliant': self.compliant,
            'compliance_checks': self.compliance_checks,
            'compliance_timestamp': self.compliance_timestamp.isoformat(),
            'violations': self.violations or []
        }

@dataclass
class MarketSummary:
    """Market summary model"""
    market_data: Dict[str, MarketData]
    trends: Dict[str, TrendAnalysis]
    predictions: Dict[str, PricePrediction]
    overall_sentiment: str
    summary_timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'market_data': {k: v.to_dict() for k, v in self.market_data.items()},
            'trends': {k: v.to_dict() for k, v in self.trends.items()},
            'predictions': {k: v.to_dict() for k, v in self.predictions.items()},
            'overall_sentiment': self.overall_sentiment,
            'summary_timestamp': self.summary_timestamp.isoformat()
        }

@dataclass
class AgentResponse:
    """Standard agent response model"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'data': self.data,
            'error': self.error,
            'error_code': self.error_code,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

def create_asset_info_from_dict(data: Dict[str, Any]) -> AssetInfo:
    """Create AssetInfo from dictionary"""
    return AssetInfo(
        asset_id=data['asset_id'],
        tier_number=data['tier_number'],
        asset_name=data['asset_name'],
        amount=data['amount'],
        price_per_unit=data['price_per_unit'],
        last_updated=datetime.fromisoformat(data['last_updated'])
    )

def create_investment_request_from_dict(data: Dict[str, Any]) -> InvestmentRequest:
    """Create InvestmentRequest from dictionary"""
    return InvestmentRequest(
        user_id=data['user_id'],
        asset_symbol=data['asset_symbol'],
        amount=data['amount'],
        quantity=data['quantity'],
        investment_type=InvestmentType(data['investment_type']),
        price=data.get('price'),
        timestamp=datetime.fromisoformat(data['timestamp']) if data.get('timestamp') else None
    )

def create_order_result_from_dict(data: Dict[str, Any]) -> OrderResult:
    """Create OrderResult from dictionary"""
    return OrderResult(
        order_id=data['order_id'],
        status=OrderStatus(data['status']),
        user_id=data['user_id'],
        asset_symbol=data['asset_symbol'],
        quantity=data['quantity'],
        executed_price=data['executed_price'],
        total_cost=data['total_cost'],
        fees=data['fees'],
        timestamp=datetime.fromisoformat(data['timestamp']),
        error_message=data.get('error_message')
    )
