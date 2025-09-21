#!/usr/bin/env python3
# Copyright 2024 Google LLC
# Bank Asset Agent - HTTP Client Utilities

import requests
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class HTTPClient:
    """HTTP client with retry logic and error handling"""
    
    def __init__(self, base_url: str = None, timeout: int = 30, max_retries: int = 3):
        self.base_url = base_url or ""
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Bank-Asset-Agent/1.0'
        })
    
    def get(self, endpoint: str, params: Dict = None, headers: Dict = None) -> Dict[str, Any]:
        """Make GET request with retry logic"""
        return self._make_request('GET', endpoint, params=params, headers=headers)
    
    def post(self, endpoint: str, data: Dict = None, headers: Dict = None) -> Dict[str, Any]:
        """Make POST request with retry logic"""
        return self._make_request('POST', endpoint, data=data, headers=headers)
    
    def put(self, endpoint: str, data: Dict = None, headers: Dict = None) -> Dict[str, Any]:
        """Make PUT request with retry logic"""
        return self._make_request('PUT', endpoint, data=data, headers=headers)
    
    def delete(self, endpoint: str, headers: Dict = None) -> Dict[str, Any]:
        """Make DELETE request with retry logic"""
        return self._make_request('DELETE', endpoint, headers=headers)
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        url = f"{self.base_url}{endpoint}" if self.base_url else endpoint
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")
                
                response = self.session.request(
                    method=method,
                    url=url,
                    timeout=self.timeout,
                    **kwargs
                )
                
                # Check if response is successful
                if response.status_code >= 200 and response.status_code < 300:
                    try:
                        return response.json()
                    except ValueError:
                        return {
                            'success': True,
                            'data': response.text,
                            'status_code': response.status_code
                        }
                else:
                    # Handle HTTP error
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    if attempt < self.max_retries - 1:
                        logger.warning(f"Request failed, retrying: {error_msg}")
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        raise requests.exceptions.HTTPError(error_msg)
                        
            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Request timeout, retrying (attempt {attempt + 1})")
                    time.sleep(2 ** attempt)
                    continue
                else:
                    raise Exception(f"Request timeout after {self.max_retries} attempts")
                    
            except requests.exceptions.ConnectionError:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Connection error, retrying (attempt {attempt + 1})")
                    time.sleep(2 ** attempt)
                    continue
                else:
                    raise Exception(f"Connection error after {self.max_retries} attempts")
                    
            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Request failed, retrying: {e}")
                    time.sleep(2 ** attempt)
                    continue
                else:
                    raise Exception(f"Request failed after {self.max_retries} attempts: {e}")
        
        # This should never be reached, but just in case
        raise Exception(f"Request failed after {self.max_retries} attempts")

class MarketReaderClient(HTTPClient):
    """Client for market-reader-svc"""
    
    def __init__(self, base_url: str = None):
        super().__init__(base_url or "http://market-reader-svc:8080")
    
    def get_market_data(self, symbols: list, time_range: str = "1d") -> Dict[str, Any]:
        """Get market data for symbols"""
        try:
            return self.get("/api/market-data", params={
                'symbols': ','.join(symbols),
                'time_range': time_range
            })
        except Exception as e:
            logger.error(f"Failed to get market data: {e}")
            raise Exception(f"Market data retrieval failed: {e}")
    
    def get_asset_info(self, symbol: str) -> Dict[str, Any]:
        """Get asset information"""
        try:
            return self.get(f"/api/assets/{symbol}")
        except Exception as e:
            logger.error(f"Failed to get asset info: {e}")
            raise Exception(f"Asset info retrieval failed: {e}")

class RuleCheckerClient(HTTPClient):
    """Client for rule-checker-svc"""
    
    def __init__(self, base_url: str = None):
        super().__init__(base_url or "http://rule-checker-svc:8080")
    
    def validate_investment(self, investment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate investment rules"""
        try:
            return self.post("/api/validate", data=investment_data)
        except Exception as e:
            logger.error(f"Failed to validate investment: {e}")
            raise Exception(f"Investment validation failed: {e}")
    
    def check_compliance(self, user_id: str, investment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check compliance requirements"""
        try:
            return self.post("/api/compliance", data={
                'user_id': user_id,
                'investment_data': investment_data
            })
        except Exception as e:
            logger.error(f"Failed to check compliance: {e}")
            raise Exception(f"Compliance check failed: {e}")

class ExecuteOrderClient(HTTPClient):
    """Client for execute-order-svc"""
    
    def __init__(self, base_url: str = None):
        super().__init__(base_url or "http://execute-order-svc:8080")
    
    def execute_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute investment order"""
        try:
            return self.post("/api/execute", data=order_data)
        except Exception as e:
            logger.error(f"Failed to execute order: {e}")
            raise Exception(f"Order execution failed: {e}")
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status"""
        try:
            return self.get(f"/api/orders/{order_id}")
        except Exception as e:
            logger.error(f"Failed to get order status: {e}")
            raise Exception(f"Order status retrieval failed: {e}")
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel order"""
        try:
            return self.post(f"/api/orders/{order_id}/cancel")
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            raise Exception(f"Order cancellation failed: {e}")

class UserRequestQueueClient(HTTPClient):
    """Client for user-request-queue-svc"""
    
    def __init__(self, base_url: str = None):
        super().__init__(base_url or "http://user-request-queue-svc:8080")
    
    def get_pending_requests(self, user_id: str = None) -> Dict[str, Any]:
        """Get pending requests"""
        try:
            params = {'user_id': user_id} if user_id else {}
            return self.get("/api/requests", params=params)
        except Exception as e:
            logger.error(f"Failed to get pending requests: {e}")
            raise Exception(f"Pending requests retrieval failed: {e}")
    
    def process_requests(self) -> Dict[str, Any]:
        """Process pending requests"""
        try:
            return self.post("/api/process")
        except Exception as e:
            logger.error(f"Failed to process requests: {e}")
            raise Exception(f"Request processing failed: {e}")
    
    def update_request_status(self, request_id: str, status: str) -> Dict[str, Any]:
        """Update request status"""
        try:
            return self.put(f"/api/requests/{request_id}", data={'status': status})
        except Exception as e:
            logger.error(f"Failed to update request status: {e}")
            raise Exception(f"Request status update failed: {e}")

class BankAssetAgentClient:
    """Main client for Bank Asset Agent operations"""
    
    def __init__(self):
        self.market_client = MarketReaderClient()
        self.rule_client = RuleCheckerClient()
        self.order_client = ExecuteOrderClient()
        self.queue_client = UserRequestQueueClient()
    
    def get_market_data(self, symbols: list, time_range: str = "1d") -> Dict[str, Any]:
        """Get market data for symbols"""
        return self.market_client.get_market_data(symbols, time_range)
    
    def validate_rules(self, investment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate investment rules"""
        return self.rule_client.validate_investment(investment_data)
    
    def execute_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute investment order"""
        return self.order_client.execute_order(order_data)
    
    def get_pending_requests(self, user_id: str = None) -> Dict[str, Any]:
        """Get pending requests"""
        return self.queue_client.get_pending_requests(user_id)

def create_http_client(service_name: str, base_url: str = None) -> HTTPClient:
    """Factory function to create HTTP clients for different services"""
    clients = {
        'market_reader': MarketReaderClient,
        'rule_checker': RuleCheckerClient,
        'execute_order': ExecuteOrderClient,
        'user_request_queue': UserRequestQueueClient
    }
    
    client_class = clients.get(service_name)
    if not client_class:
        raise ValueError(f"Unknown service: {service_name}")
    
    return client_class(base_url)
