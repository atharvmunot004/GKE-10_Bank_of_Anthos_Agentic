#!/usr/bin/env python3
# Copyright 2024 Google LLC
# Bank Asset Agent - gRPC Service Implementation

import grpc
import logging
from concurrent import futures
from typing import Dict, Any

logger = logging.getLogger(__name__)

def create_grpc_client(host: str = 'bank-asset-agent', port: int = 8080):
    """Create gRPC client connection"""
    try:
        channel = grpc.insecure_channel(f'{host}:{port}')
        return channel
    except Exception as e:
        logger.error(f"Failed to create gRPC client: {e}")
        raise Exception(f"gRPC client creation failed: {e}")

def handle_grpc_error(error: Exception) -> Dict[str, Any]:
    """Handle gRPC errors and return standardized error response"""
    try:
        if isinstance(error, grpc.RpcError):
            error_code = error.code()
            error_message = error.details()
            
            return {
                'error': True,
                'error_code': str(error_code),
                'message': error_message,
                'error_type': 'grpc_error'
            }
        else:
            return {
                'error': True,
                'error_code': 'UNKNOWN',
                'message': str(error),
                'error_type': 'unknown_error'
            }
    except Exception as e:
        logger.error(f"Failed to handle gRPC error: {e}")
        return {
            'error': True,
            'error_code': 'ERROR_HANDLING_FAILED',
            'message': 'Failed to handle error',
            'error_type': 'error_handling_failed'
        }

class BankAssetAgentService:
    """gRPC service implementation for Bank Asset Agent"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def AnalyzeMarketData(self, request, context):
        """Analyze market data and provide insights"""
        try:
            self.logger.info(f"Analyzing market data for symbols: {request.asset_symbols}")
            
            # Import here to avoid circular imports
            from agents.market_analyzer import MarketAnalyzer
            
            analyzer = MarketAnalyzer()
            market_data = analyzer.get_market_data(request.asset_symbols, request.time_range)
            trends = analyzer.analyze_trends(market_data)
            
            return {
                'success': True,
                'market_data': market_data,
                'trends': trends,
                'analysis_timestamp': trends.get('analysis_timestamp')
            }
        except Exception as e:
            self.logger.error(f"Failed to analyze market data: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Market data analysis failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def ProcessInvestmentRequest(self, request, context):
        """Process investment requests from the queue"""
        try:
            self.logger.info(f"Processing investment request for user: {request.user_id}")
            
            # Import here to avoid circular imports
            from agents.rule_validator import RuleValidator
            from agents.order_executor import OrderExecutor
            
            # Validate rules first
            validator = RuleValidator()
            rule_validation = validator.validate_investment_rules({
                'user_id': request.user_id,
                'asset_symbol': request.asset_symbol,
                'amount': request.amount,
                'investment_type': request.investment_type
            })
            
            if not rule_validation.get('valid', False):
                return {
                    'success': False,
                    'error': 'Rule validation failed',
                    'validation_details': rule_validation
                }
            
            # Execute order if validation passes
            executor = OrderExecutor()
            order_result = executor.execute_order({
                'user_id': request.user_id,
                'asset_symbol': request.asset_symbol,
                'quantity': request.quantity,
                'order_type': request.investment_type,
                'price': request.price
            })
            
            return {
                'success': True,
                'order_result': order_result,
                'validation_result': rule_validation
            }
        except Exception as e:
            self.logger.error(f"Failed to process investment request: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Investment request processing failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def ExecuteAssetManagement(self, request, context):
        """Execute asset management operations"""
        try:
            self.logger.info(f"Executing asset management operation: {request.operation}")
            
            # Import here to avoid circular imports
            from utils.db_client import AssetsDatabaseClient
            
            db_client = AssetsDatabaseClient()
            
            if request.operation == 'update_price':
                result = db_client.update_asset_price(request.asset_id, request.new_price)
            elif request.operation == 'update_availability':
                result = db_client.update_asset_availability(request.asset_id, request.amount)
            elif request.operation == 'add_asset':
                result = db_client.add_asset({
                    'tier_number': request.tier_number,
                    'asset_name': request.asset_name,
                    'amount': request.amount,
                    'price_per_unit': request.price_per_unit
                })
            else:
                raise ValueError(f"Unknown operation: {request.operation}")
            
            return {
                'success': result,
                'operation': request.operation,
                'timestamp': request.timestamp
            }
        except Exception as e:
            self.logger.error(f"Failed to execute asset management: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Asset management execution failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def ValidateInvestmentRules(self, request, context):
        """Validate investment rules and compliance"""
        try:
            self.logger.info(f"Validating investment rules for user: {request.user_id}")
            
            # Import here to avoid circular imports
            from agents.rule_validator import RuleValidator
            
            validator = RuleValidator()
            
            # Validate rules
            rule_validation = validator.check_investment_rules({
                'asset_symbol': request.investment_data.get('asset_symbol'),
                'amount': request.investment_data.get('amount'),
                'investment_type': request.investment_data.get('investment_type')
            })
            
            # Assess risk
            risk_assessment = validator.assess_risk({
                'asset_symbol': request.investment_data.get('asset_symbol'),
                'amount': request.investment_data.get('amount'),
                'investment_type': request.investment_data.get('investment_type')
            })
            
            # Validate compliance
            compliance_validation = validator.validate_compliance(
                request.investment_data,
                {'user_id': request.user_id}
            )
            
            return {
                'success': True,
                'rule_validation': rule_validation,
                'risk_assessment': risk_assessment,
                'compliance_validation': compliance_validation
            }
        except Exception as e:
            self.logger.error(f"Failed to validate investment rules: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Investment rules validation failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

def start_grpc_server(port: int = 8080):
    """Start gRPC server"""
    try:
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        
        # Add service to server
        service = BankAssetAgentService()
        # Note: In a real implementation, you would register the service properly
        
        server.add_insecure_port(f'[::]:{port}')
        server.start()
        
        logger.info(f"gRPC server started on port {port}")
        return server
    except Exception as e:
        logger.error(f"Failed to start gRPC server: {e}")
        raise Exception(f"gRPC server startup failed: {e}")
