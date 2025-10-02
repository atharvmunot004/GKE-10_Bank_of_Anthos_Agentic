"""
Unit tests for FastAPI application
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime

from main import app
from models import HealthResponse


class TestFastAPIEndpoints:
    """Test FastAPI endpoints"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_health_check_healthy(self):
        """Test health check endpoint - healthy"""
        with patch('database.db_manager.is_connected', new_callable=AsyncMock, return_value=True):
            with patch('services.queue_processor.asset_agent_client.is_available', 
                      new_callable=AsyncMock, return_value=True):
                
                response = self.client.get("/health")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert data["database_connected"] is True
                assert data["external_service_available"] is True
    
    def test_health_check_unhealthy_database(self):
        """Test health check endpoint - database unhealthy"""
        with patch('database.db_manager.is_connected', new_callable=AsyncMock, return_value=False):
            with patch('services.queue_processor.asset_agent_client.is_available', 
                      new_callable=AsyncMock, return_value=True):
                
                response = self.client.get("/health")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "unhealthy"
                assert data["database_connected"] is False
                assert data["external_service_available"] is True
    
    def test_health_check_unhealthy_external_service(self):
        """Test health check endpoint - external service unhealthy"""
        with patch('database.db_manager.is_connected', new_callable=AsyncMock, return_value=True):
            with patch('services.queue_processor.asset_agent_client.is_available', 
                      new_callable=AsyncMock, return_value=False):
                
                response = self.client.get("/health")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "unhealthy"
                assert data["database_connected"] is True
                assert data["external_service_available"] is False
    
    def test_health_check_exception(self):
        """Test health check endpoint - exception handling"""
        with patch('database.db_manager.is_connected', 
                  new_callable=AsyncMock, side_effect=Exception("Database error")):
            
            response = self.client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["database_connected"] is False
            assert data["external_service_available"] is False
    
    def test_readiness_check_ready(self):
        """Test readiness check endpoint - ready"""
        with patch('database.db_manager.is_connected', new_callable=AsyncMock, return_value=True):
            
            response = self.client.get("/ready")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"
    
    def test_readiness_check_not_ready(self):
        """Test readiness check endpoint - not ready"""
        with patch('database.db_manager.is_connected', new_callable=AsyncMock, return_value=False):
            
            response = self.client.get("/ready")
            
            assert response.status_code == 503
            data = response.json()
            assert "Database not connected" in data["detail"]
    
    def test_readiness_check_exception(self):
        """Test readiness check endpoint - exception"""
        with patch('database.db_manager.is_connected', 
                  new_callable=AsyncMock, side_effect=Exception("Database error")):
            
            response = self.client.get("/ready")
            
            assert response.status_code == 503
            data = response.json()
            assert "Service not ready" in data["detail"]
    
    def test_metrics_endpoint(self):
        """Test metrics endpoint"""
        with patch('database.db_manager.count_pending_requests', 
                  new_callable=AsyncMock, return_value=25):
            with patch('utils.get_metrics', return_value="# HELP test_metric Test metric\ntest_metric 1.0"):
                
                response = self.client.get("/metrics")
                
                assert response.status_code == 200
                assert response.headers["content-type"] == "text/plain; charset=utf-8"
                assert "test_metric" in response.text
    
    def test_metrics_endpoint_exception(self):
        """Test metrics endpoint exception handling"""
        with patch('database.db_manager.count_pending_requests', 
                  new_callable=AsyncMock, side_effect=Exception("Database error")):
            
            response = self.client.get("/metrics")
            
            assert response.status_code == 500
            data = response.json()
            assert "Metrics collection failed" in data["detail"]
    
    def test_force_poll_endpoint(self):
        """Test force poll endpoint"""
        response = self.client.post("/api/v1/poll")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Polling triggered"
        assert "timestamp" in data
    
    def test_get_batch_status_endpoint(self):
        """Test get batch status endpoint"""
        batch_id = "test-batch-123"
        
        response = self.client.get(f"/api/v1/batch/{batch_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["batch_id"] == batch_id
        assert data["status"] == "unknown"
        assert data["transaction_count"] == 0
        assert "created_at" in data
    
    def test_get_queue_stats_endpoint(self):
        """Test get queue stats endpoint"""
        with patch('database.db_manager.count_pending_requests', 
                  new_callable=AsyncMock, return_value=42):
            
            response = self.client.get("/api/v1/queue/stats")
            
            assert response.status_code == 200
            data = response.json()
            assert data["pending_requests"] == 42
            assert data["batch_size"] == 10
            assert data["polling_interval"] == 5
            assert "timestamp" in data
    
    def test_get_queue_stats_exception(self):
        """Test get queue stats endpoint exception handling"""
        with patch('database.db_manager.count_pending_requests', 
                  new_callable=AsyncMock, side_effect=Exception("Database error")):
            
            response = self.client.get("/api/v1/queue/stats")
            
            assert response.status_code == 500
            data = response.json()
            assert "Failed to get queue stats" in data["detail"]
    
    def test_invalid_endpoint(self):
        """Test invalid endpoint"""
        response = self.client.get("/invalid/endpoint")
        
        assert response.status_code == 404
    
    def test_cors_headers(self):
        """Test CORS headers if configured"""
        response = self.client.get("/health")
        
        # Basic response check
        assert response.status_code == 200
    
    def test_api_documentation(self):
        """Test API documentation endpoints"""
        # Test OpenAPI schema
        response = self.client.get("/openapi.json")
        assert response.status_code == 200
        
        # Test Swagger UI
        response = self.client.get("/docs")
        assert response.status_code == 200
        
        # Test ReDoc
        response = self.client.get("/redoc")
        assert response.status_code == 200


class TestAPIErrorHandling:
    """Test API error handling"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_method_not_allowed(self):
        """Test method not allowed error"""
        response = self.client.post("/health")  # GET endpoint called with POST
        
        assert response.status_code == 405
    
    def test_validation_error(self):
        """Test request validation error"""
        # This would test validation if we had POST endpoints with request bodies
        # For now, we'll test with invalid path parameters
        response = self.client.get("/api/v1/batch//status")  # Empty batch_id
        
        assert response.status_code == 422 or response.status_code == 404
    
    def test_internal_server_error_handling(self):
        """Test internal server error handling"""
        # This tests the global exception handler
        with patch('database.db_manager.is_connected', 
                  new_callable=AsyncMock, side_effect=Exception("Unexpected error")):
            
            response = self.client.get("/health")
            
            # The health endpoint has its own exception handling
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unhealthy"


class TestAPIPerformance:
    """Test API performance characteristics"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_concurrent_health_checks(self):
        """Test concurrent health check requests"""
        import concurrent.futures
        import threading
        
        def make_request():
            with patch('database.db_manager.is_connected', new_callable=AsyncMock, return_value=True):
                with patch('services.queue_processor.asset_agent_client.is_available', 
                          new_callable=AsyncMock, return_value=True):
                    return self.client.get("/health")
        
        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
    
    def test_response_time_health_check(self):
        """Test health check response time"""
        import time
        
        with patch('database.db_manager.is_connected', new_callable=AsyncMock, return_value=True):
            with patch('services.queue_processor.asset_agent_client.is_available', 
                      new_callable=AsyncMock, return_value=True):
                
                start_time = time.time()
                response = self.client.get("/health")
                end_time = time.time()
                
                assert response.status_code == 200
                # Health check should be fast (under 1 second)
                assert (end_time - start_time) < 1.0
