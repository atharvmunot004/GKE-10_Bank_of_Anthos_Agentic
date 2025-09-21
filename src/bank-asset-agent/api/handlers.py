#!/usr/bin/env python3
# Copyright 2024 Google LLC
# Bank Asset Agent - API Handlers

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

def analyze_market_data_handler(request_data: Dict, context: Any) -> Dict:
    """Handle market data analysis requests"""
    try:
        logger.info(f"Handling market data analysis request: {request_data}")
        
        from agents.market_analyzer import MarketAnalyzer
        
        analyzer = MarketAnalyzer()
        
        # Get market data
        market_data = analyzer.get_market_data(
            request_data.get('asset_symbols', []),
            request_data.get('time_range', '1d')
        )
        
        # Analyze trends
        trends = analyzer.analyze_trends(market_data)
        
        # Get predictions if requested
        predictions = None
        if request_data.get('include_predictions', False):
            predictions = analyzer.predict_prices(
                request_data.get('asset_symbols', []),
                request_data.get('prediction_horizon', '1h')
            )
        
        return {
            'success': True,
            'market_data': market_data,
            'trends': trends,
            'predictions': predictions,
            'analysis_timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to handle market data analysis: {e}")
        return handle_http_error(e)

def process_investment_request_handler(request_data: Dict, context: Any) -> Dict:
    """Handle investment request processing"""
    try:
        logger.info(f"Handling investment request: {request_data}")
        
        from agents.rule_validator import RuleValidator
        from agents.order_executor import OrderExecutor
        
        # Validate rules first
        validator = RuleValidator()
        rule_validation = validator.validate_investment_rules(request_data)
        
        if not rule_validation.get('valid', False):
            return {
                'success': False,
                'error': 'Rule validation failed',
                'validation_details': rule_validation
            }
        
        # Execute order if validation passes
        executor = OrderExecutor()
        order_result = executor.execute_order(request_data)
        
        return {
            'success': True,
            'order_result': order_result,
            'validation_result': rule_validation,
            'processing_timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to handle investment request: {e}")
        return handle_http_error(e)

def execute_asset_management_handler(request_data: Dict, context: Any) -> Dict:
    """Handle asset management operations"""
    try:
        logger.info(f"Handling asset management operation: {request_data}")
        
        from utils.db_client import AssetsDatabaseClient
        
        db_client = AssetsDatabaseClient()
        operation = request_data.get('operation')
        
        if operation == 'update_price':
            result = db_client.update_asset_price(
                request_data.get('asset_id'),
                request_data.get('new_price')
            )
        elif operation == 'update_availability':
            result = db_client.update_asset_availability(
                request_data.get('asset_id'),
                request_data.get('amount')
            )
        elif operation == 'add_asset':
            result = db_client.add_asset({
                'tier_number': request_data.get('tier_number'),
                'asset_name': request_data.get('asset_name'),
                'amount': request_data.get('amount'),
                'price_per_unit': request_data.get('price_per_unit')
            })
        elif operation == 'get_asset_info':
            result = db_client.get_asset_info(request_data.get('asset_id'))
        else:
            raise ValueError(f"Unknown operation: {operation}")
        
        return {
            'success': result is not None,
            'operation': operation,
            'result': result,
            'execution_timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to handle asset management: {e}")
        return handle_http_error(e)

def validate_investment_rules_handler(request_data: Dict, context: Any) -> Dict:
    """Handle investment rules validation"""
    try:
        logger.info(f"Handling investment rules validation: {request_data}")
        
        from agents.rule_validator import RuleValidator
        
        validator = RuleValidator()
        
        # Validate rules
        rule_validation = validator.check_investment_rules(
            request_data.get('investment_data', {})
        )
        
        # Assess risk
        risk_assessment = validator.assess_risk(
            request_data.get('investment_data', {})
        )
        
        # Validate compliance
        compliance_validation = validator.validate_compliance(
            request_data.get('investment_data', {}),
            {'user_id': request_data.get('user_id')}
        )
        
        return {
            'success': True,
            'rule_validation': rule_validation,
            'risk_assessment': risk_assessment,
            'compliance_validation': compliance_validation,
            'validation_timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to handle investment rules validation: {e}")
        return handle_http_error(e)

def handle_http_error(error: Exception) -> Dict:
    """Handle HTTP errors and return standardized error response"""
    try:
        error_message = str(error)
        error_type = type(error).__name__
        
        # Determine error code based on error type
        if 'timeout' in error_message.lower():
            error_code = 'TIMEOUT'
        elif 'connection' in error_message.lower():
            error_code = 'CONNECTION_ERROR'
        elif 'validation' in error_message.lower():
            error_code = 'VALIDATION_ERROR'
        else:
            error_code = 'UNKNOWN_ERROR'
        
        return {
            'success': False,
            'error': True,
            'error_code': error_code,
            'error_type': error_type,
            'message': error_message,
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to handle HTTP error: {e}")
        return {
            'success': False,
            'error': True,
            'error_code': 'ERROR_HANDLING_FAILED',
            'error_type': 'ErrorHandlingFailed',
            'message': 'Failed to handle error',
            'timestamp': datetime.utcnow().isoformat()
        }

def handle_database_error(error: Exception) -> Dict:
    """Handle database errors and return standardized error response"""
    try:
        error_message = str(error)
        error_type = type(error).__name__
        
        # Determine error code based on error type
        if 'connection' in error_message.lower():
            error_code = 'DB_CONNECTION_ERROR'
        elif 'timeout' in error_message.lower():
            error_code = 'DB_TIMEOUT'
        elif 'constraint' in error_message.lower():
            error_code = 'DB_CONSTRAINT_ERROR'
        elif 'permission' in error_message.lower():
            error_code = 'DB_PERMISSION_ERROR'
        else:
            error_code = 'DB_UNKNOWN_ERROR'
        
        return {
            'success': False,
            'error': True,
            'error_code': error_code,
            'error_type': error_type,
            'message': error_message,
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to handle database error: {e}")
        return {
            'success': False,
            'error': True,
            'error_code': 'DB_ERROR_HANDLING_FAILED',
            'error_type': 'DatabaseErrorHandlingFailed',
            'message': 'Failed to handle database error',
            'timestamp': datetime.utcnow().isoformat()
        }

def validate_request_data(request_data: Dict, required_fields: list) -> Dict:
    """Validate request data has required fields"""
    try:
        missing_fields = []
        for field in required_fields:
            if field not in request_data or request_data[field] is None:
                missing_fields.append(field)
        
        if missing_fields:
            return {
                'valid': False,
                'missing_fields': missing_fields,
                'message': f"Missing required fields: {', '.join(missing_fields)}"
            }
        
        return {
            'valid': True,
            'message': 'Request data is valid'
        }
    except Exception as e:
        logger.error(f"Failed to validate request data: {e}")
        return {
            'valid': False,
            'error': str(e),
            'message': 'Request validation failed'
        }

def log_request(request_data: Dict, handler_name: str) -> None:
    """Log request data for debugging"""
    try:
        logger.info(f"Processing {handler_name} request: {request_data}")
    except Exception as e:
        logger.error(f"Failed to log request: {e}")

def log_response(response_data: Dict, handler_name: str) -> None:
    """Log response data for debugging"""
    try:
        logger.info(f"Completed {handler_name} response: {response_data.get('success', False)}")
    except Exception as e:
        logger.error(f"Failed to log response: {e}")
