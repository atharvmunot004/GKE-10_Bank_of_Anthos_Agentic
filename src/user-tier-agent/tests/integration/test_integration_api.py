"""
Integration tests for API endpoints
"""

import pytest
import json
import uuid
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

from app.models.schemas import PurposeEnum, TierAllocation


class TestIntegrationAPI:
    """Integration tests for API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        from main import app
        return TestClient(app)
    
    @pytest.fixture
    def valid_request_data(self):
        """Valid request data for testing"""
        return {
            "uuid": str(uuid.uuid4()),
            "accountid": "test-account-123",
            "amount": 10000.0,
            "purpose": "INVEST"
        }
    
    def test_allocate_tiers_success(self, client, valid_request_data):
        """Test successful tier allocation"""
        with patch('app.services.agent.tier_allocation_agent.allocate_tiers') as mock_allocate:
            mock_allocate.return_value = TierAllocation(
                tier1=1000.0,
                tier2=2000.0,
                tier3=7000.0
            )
            
            response = client.post("/api/v1/allocation/allocate-tiers", json=valid_request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "allocation" in data
            assert data["allocation"]["tier1"] == 1000.0
            assert data["allocation"]["tier2"] == 2000.0
            assert data["allocation"]["tier3"] == 7000.0
            assert "reasoning" in data
            assert "request_id" in data
    
    def test_allocate_tiers_validation_error(self, client):
        """Test tier allocation with validation error"""
        invalid_request_data = {
            "uuid": "invalid-uuid",
            "accountid": "",
            "amount": -1000.0,
            "purpose": "INVALID"
        }
        
        response = client.post("/api/v1/allocation/allocate-tiers", json=invalid_request_data)
        
        assert response.status_code == 422  # FastAPI returns 422 for validation errors
        data = response.json()
        assert "detail" in data  # FastAPI validation errors use 'detail' field
        assert isinstance(data["detail"], list)  # Detail is a list of validation errors
        assert len(data["detail"]) >= 4  # Should have validation errors for all fields
    
    def test_allocate_tiers_agent_failure_fallback(self, client, valid_request_data):
        """Test tier allocation with agent failure and fallback to default"""
        with patch('app.services.agent.tier_allocation_agent.allocate_tiers') as mock_allocate:
            mock_allocate.side_effect = Exception("Agent failed")
            
            with patch('app.services.agent.tier_allocation_agent.get_default_allocation') as mock_default:
                mock_default.return_value = TierAllocation(
                    tier1=2000.0,
                    tier2=3000.0,
                    tier3=5000.0
                )
                
                response = client.post("/api/v1/allocation/allocate-tiers", json=valid_request_data)
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "Default tier allocation used due to agent failure" in data["reasoning"]
    
    def test_allocate_tiers_withdraw_purpose(self, client):
        """Test tier allocation for withdrawal purpose"""
        request_data = {
            "uuid": str(uuid.uuid4()),
            "accountid": "test-account-456",
            "amount": 5000.0,
            "purpose": "WITHDRAW"
        }
        
        with patch('app.services.agent.tier_allocation_agent.allocate_tiers') as mock_allocate:
            mock_allocate.return_value = Mock(
                tier1=1000.0,
                tier2=1500.0,
                tier3=2500.0
            )
            
            response = client.post("/api/v1/allocation/allocate-tiers", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["allocation"]["tier1"] == 1000.0
            assert data["allocation"]["tier2"] == 1500.0
            assert data["allocation"]["tier3"] == 2500.0
    
    def test_get_default_allocation_success(self, client):
        """Test getting default allocation"""
        with patch('app.services.agent.tier_allocation_agent.get_default_allocation') as mock_default:
            mock_default.return_value = TierAllocation(
                tier1=1000.0,
                tier2=1500.0,
                tier3=2500.0
            )
            
            response = client.get("/api/v1/allocation/allocate-tiers/test-account-123/default?amount=5000.0")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "allocation" in data
            assert "Default tier allocation" in data["reasoning"]
    
    def test_get_default_allocation_invalid_accountid(self, client):
        """Test getting default allocation with invalid account ID"""
        response = client.get("/api/v1/allocation/allocate-tiers//default?amount=5000.0")
        
        assert response.status_code == 404  # FastAPI returns 404 for invalid paths
    
    def test_get_default_allocation_invalid_amount(self, client):
        """Test getting default allocation with invalid amount"""
        response = client.get("/api/v1/allocation/allocate-tiers/test-account-123/default?amount=-1000.0")
        
        assert response.status_code == 400
    
    def test_health_check_endpoint(self, client):
        """Test health check endpoint"""
        with patch('app.core.health.HealthChecker.check_health') as mock_health:
            mock_health.return_value = {
                "status": "healthy",
                "dependencies": [
                    {
                        "name": "ledger-db",
                        "status": "healthy"
                    }
                ]
            }
            
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "version" in data
    
    def test_health_check_unhealthy(self, client):
        """Test health check endpoint when unhealthy"""
        with patch('app.core.health.HealthChecker.check_health') as mock_health:
            mock_health.return_value = {
                "status": "unhealthy",
                "dependencies": [
                    {
                        "name": "ledger-db",
                        "status": "unhealthy"
                    }
                ]
            }
            
            response = client.get("/health")
            
            assert response.status_code == 503
    
    def test_readiness_check_endpoint(self, client):
        """Test readiness check endpoint"""
        with patch('app.core.health.HealthChecker.check_readiness') as mock_readiness:
            mock_readiness.return_value = {
                "ready": True,
                "dependencies": [
                    {
                        "name": "ledger-db",
                        "status": "healthy"
                    }
                ]
            }
            
            response = client.get("/ready")
            
            assert response.status_code == 200
            data = response.json()
            assert data["ready"] is True
            assert "version" in data
    
    def test_readiness_check_not_ready(self, client):
        """Test readiness check endpoint when not ready"""
        with patch('app.core.health.HealthChecker.check_readiness') as mock_readiness:
            mock_readiness.return_value = {
                "ready": False,
                "dependencies": [
                    {
                        "name": "ledger-db",
                        "status": "unhealthy"
                    }
                ]
            }
            
            response = client.get("/ready")
            
            assert response.status_code == 503
    
    def test_metrics_endpoint(self, client):
        """Test metrics endpoint"""
        response = client.get("/metrics")
        
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        assert "http_requests_total" in response.text
    
    def test_concurrent_requests(self, client, valid_request_data):
        """Test handling concurrent requests"""
        import threading
        import time
        
        results = []
        
        def make_request():
            with patch('app.services.agent.tier_allocation_agent.allocate_tiers') as mock_allocate:
                mock_allocate.return_value = Mock(
                    tier1=1000.0,
                    tier2=2000.0,
                    tier3=7000.0
                )
                
                response = client.post("/api/v1/allocation/allocate-tiers", json=valid_request_data)
                results.append(response.status_code)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert all(status == 200 for status in results)
        assert len(results) == 5
    
    def test_request_id_middleware(self, client, valid_request_data):
        """Test request ID middleware"""
        with patch('app.services.agent.tier_allocation_agent.allocate_tiers') as mock_allocate:
            mock_allocate.return_value = TierAllocation(
                tier1=1000.0,
                tier2=2000.0,
                tier3=7000.0
            )
            
            response = client.post("/api/v1/allocation/allocate-tiers", json=valid_request_data)
            
            assert response.status_code == 200
            assert "X-Request-ID" in response.headers
            
            data = response.json()
            assert "request_id" in data
            assert data["request_id"] == response.headers["X-Request-ID"]
    
    def test_custom_request_id_header(self, client, valid_request_data):
        """Test custom request ID header"""
        custom_request_id = "custom-request-123"
        
        with patch('app.services.agent.tier_allocation_agent.allocate_tiers') as mock_allocate:
            mock_allocate.return_value = TierAllocation(
                tier1=1000.0,
                tier2=2000.0,
                tier3=7000.0
            )
            
            response = client.post(
                "/api/v1/allocation/allocate-tiers",
                json=valid_request_data,
                headers={"X-Request-ID": custom_request_id}
            )
            
            assert response.status_code == 200
            assert response.headers["X-Request-ID"] == custom_request_id
            
            data = response.json()
            assert data["request_id"] == custom_request_id
