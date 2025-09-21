#!/usr/bin/env python3
# Copyright 2024 Google LLC
# Bank Asset Agent - Order Executor

import requests
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class OrderExecutor:
    """AI agent for investment order execution and management"""
    
    def __init__(self, execute_order_url: str = None):
        self.execute_order_url = execute_order_url or os.environ.get('EXECUTE_ORDER_URL', 'http://execute-order-svc:8080')
    
    def execute_buy_order(self, order_data: Dict) -> Dict:
        """Execute a buy order"""
        try:
            order_data['order_type'] = 'buy'
            order_data['order_id'] = str(uuid.uuid4())
            order_data['timestamp'] = datetime.utcnow().isoformat()
            
            response = requests.post(
                f"{self.execute_order_url}/api/execute",
                json=order_data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to execute buy order: {e}")
            raise Exception(f"Buy order execution failed: {e}")
    
    def execute_sell_order(self, order_data: Dict) -> Dict:
        """Execute a sell order"""
        try:
            order_data['order_type'] = 'sell'
            order_data['order_id'] = str(uuid.uuid4())
            order_data['timestamp'] = datetime.utcnow().isoformat()
            
            response = requests.post(
                f"{self.execute_order_url}/api/execute",
                json=order_data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to execute sell order: {e}")
            raise Exception(f"Sell order execution failed: {e}")
    
    def execute_order(self, order_data: Dict) -> Dict:
        """Execute an investment order (generic)"""
        try:
            order_type = order_data.get('order_type', 'buy')
            
            if order_type == 'buy':
                return self.execute_buy_order(order_data)
            elif order_type == 'sell':
                return self.execute_sell_order(order_data)
            else:
                raise ValueError(f"Invalid order type: {order_type}")
        except Exception as e:
            logger.error(f"Failed to execute order: {e}")
            raise Exception(f"Order execution failed: {e}")
    
    def monitor_order_status(self, order_id: str) -> Dict:
        """Monitor order execution status"""
        try:
            response = requests.get(
                f"{self.execute_order_url}/api/orders/{order_id}",
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to monitor order status: {e}")
            raise Exception(f"Order status monitoring failed: {e}")
    
    def cancel_order(self, order_id: str) -> Dict:
        """Cancel a pending order"""
        try:
            response = requests.post(
                f"{self.execute_order_url}/api/orders/{order_id}/cancel",
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to cancel order: {e}")
            raise Exception(f"Order cancellation failed: {e}")
    
    def get_order_history(self, user_id: str, limit: int = 50) -> Dict:
        """Get order history for a user"""
        try:
            response = requests.get(
                f"{self.execute_order_url}/api/orders",
                params={'user_id': user_id, 'limit': limit},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get order history: {e}")
            raise Exception(f"Order history retrieval failed: {e}")
    
    def validate_order(self, order_data: Dict) -> Dict:
        """Validate order before execution"""
        try:
            validation_result = {
                'valid': True,
                'errors': [],
                'warnings': []
            }
            
            # Check required fields
            required_fields = ['user_id', 'asset_symbol', 'quantity', 'order_type']
            for field in required_fields:
                if field not in order_data or not order_data[field]:
                    validation_result['errors'].append(f"Missing required field: {field}")
                    validation_result['valid'] = False
            
            # Validate order type
            if order_data.get('order_type') not in ['buy', 'sell']:
                validation_result['errors'].append("Invalid order type. Must be 'buy' or 'sell'")
                validation_result['valid'] = False
            
            # Validate quantity
            quantity = order_data.get('quantity', 0)
            if quantity <= 0:
                validation_result['errors'].append("Quantity must be greater than 0")
                validation_result['valid'] = False
            
            # Validate price (if provided)
            price = order_data.get('price', 0)
            if price and price <= 0:
                validation_result['errors'].append("Price must be greater than 0")
                validation_result['valid'] = False
            
            # Check for warnings
            if quantity > 1000:
                validation_result['warnings'].append("Large order quantity detected")
            
            return validation_result
        except Exception as e:
            logger.error(f"Failed to validate order: {e}")
            raise Exception(f"Order validation failed: {e}")
    
    def calculate_order_cost(self, order_data: Dict) -> Dict:
        """Calculate order cost and fees"""
        try:
            quantity = order_data.get('quantity', 0)
            price = order_data.get('price', 0)
            order_type = order_data.get('order_type', 'buy')
            
            # Calculate base cost
            base_cost = quantity * price
            
            # Calculate fees (simplified)
            fee_rate = 0.001  # 0.1% fee
            fees = base_cost * fee_rate
            
            # Calculate total cost
            if order_type == 'buy':
                total_cost = base_cost + fees
            else:  # sell
                total_cost = base_cost - fees
            
            return {
                'base_cost': base_cost,
                'fees': fees,
                'total_cost': total_cost,
                'fee_rate': fee_rate,
                'order_type': order_type
            }
        except Exception as e:
            logger.error(f"Failed to calculate order cost: {e}")
            raise Exception(f"Order cost calculation failed: {e}")
    
    def execute_batch_orders(self, orders: List[Dict]) -> Dict:
        """Execute multiple orders in batch"""
        try:
            results = []
            successful_orders = 0
            failed_orders = 0
            
            for order_data in orders:
                try:
                    # Validate order first
                    validation = self.validate_order(order_data)
                    if not validation['valid']:
                        results.append({
                            'order_id': order_data.get('order_id'),
                            'status': 'failed',
                            'error': 'Validation failed',
                            'errors': validation['errors']
                        })
                        failed_orders += 1
                        continue
                    
                    # Execute order
                    result = self.execute_order(order_data)
                    results.append(result)
                    
                    if result.get('status') == 'executed':
                        successful_orders += 1
                    else:
                        failed_orders += 1
                        
                except Exception as e:
                    results.append({
                        'order_id': order_data.get('order_id'),
                        'status': 'failed',
                        'error': str(e)
                    })
                    failed_orders += 1
            
            return {
                'batch_results': results,
                'successful_orders': successful_orders,
                'failed_orders': failed_orders,
                'total_orders': len(orders),
                'batch_timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to execute batch orders: {e}")
            raise Exception(f"Batch order execution failed: {e}")
    
    def get_execution_statistics(self, user_id: str, time_period: str = "30d") -> Dict:
        """Get execution statistics for a user"""
        try:
            response = requests.get(
                f"{self.execute_order_url}/api/statistics",
                params={'user_id': user_id, 'time_period': time_period},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get execution statistics: {e}")
            raise Exception(f"Execution statistics retrieval failed: {e}")
