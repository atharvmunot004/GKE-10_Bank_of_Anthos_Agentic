"""
End-to-end tests for complete workflows
"""

import pytest
import json
import uuid
import time
from unittest.mock import patch, Mock
import httpx
from fastapi.testclient import TestClient

from main import app
from app.models.schemas import PurposeEnum, TierAllocation


class TestEndToEndWorkflow:
    """End-to-end tests for complete workflows"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_external_services(self):
        """Mock external services for E2E testing"""
        with patch('httpx.get') as mock_get, \
             patch('httpx.post') as mock_post:
            
            # Mock ledger-db responses
            mock_get.return_value.json.return_value = {
                "transactions": [
                    {
                        "transaction_id": "tx-001",
                        "from_acct": "test-account-123",
                        "to_acct": "merchant-001",
                        "from_route": "123456789",
                        "to_route": "987654321",
                        "amount": 50.0,
                        "timestamp": "2024-01-01T10:00:00Z"
                    },
                    {
                        "transaction_id": "tx-002",
                        "from_acct": "employer-001",
                        "to_acct": "test-account-123",
                        "from_route": "111111111",
                        "to_route": "123456789",
                        "amount": 5000.0,
                        "timestamp": "2024-01-01T09:00:00Z"
                    }
                ]
            }
            mock_get.return_value.raise_for_status.return_value = None
            
            # Mock queue-db responses
            mock_post.return_value.json.return_value = {
                "status": "success",
                "id": "queue-123",
                "timestamp": "2024-01-01T10:00:00Z"
            }
            mock_post.return_value.raise_for_status.return_value = None
            
            yield mock_get, mock_post
    
    def test_end_to_end_investment_flow(self, client, mock_external_services):
        """Test complete investment workflow"""
        mock_get, mock_post = mock_external_services
        
        # Mock agent response
        with patch('app.services.agent.tier_allocation_agent.allocate_tiers') as mock_allocate:
            mock_allocate.return_value = TierAllocation(
                tier1=1000.0,
                tier2=2000.0,
                tier3=7000.0
            )
            
            # Step 1: Make investment allocation request
            request_data = {
                "uuid": str(uuid.uuid4()),
                "accountid": "test-account-123",
                "amount": 10000.0,
                "purpose": "INVEST"
            }
            
            response = client.post("/api/v1/allocation/allocate-tiers", json=request_data)
            
            # Step 2: Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "allocation" in data
            assert data["allocation"]["tier1"] == 1000.0
            assert data["allocation"]["tier2"] == 2000.0
            assert data["allocation"]["tier3"] == 7000.0
            
            # Step 3: Verify successful response
            # Note: External service calls are bypassed when agent is mocked
            # In real E2E tests, we would verify external service calls
            
            # Step 4: Verify service health (mock health check for E2E tests)
            with patch('app.core.health.HealthChecker.check_health') as mock_health:
                mock_health.return_value = {
                    "status": "healthy",
                    "dependencies": [
                        {"name": "ledger-db", "status": "healthy"},
                        {"name": "queue-db", "status": "healthy"},
                        {"name": "portfolio-db", "status": "healthy"},
                        {"name": "gemini-api", "status": "healthy"}
                    ]
                }
                health_response = client.get("/health")
                assert health_response.status_code == 200
            
            # Step 5: Verify readiness (mock readiness check for E2E tests)
            with patch('app.core.health.HealthChecker.check_readiness') as mock_readiness:
                mock_readiness.return_value = {
                    "ready": True,
                    "dependencies": [
                        {"name": "ledger-db", "status": "healthy"},
                        {"name": "queue-db", "status": "healthy"}
                    ]
                }
                readiness_response = client.get("/ready")
                assert readiness_response.status_code == 200
    
    def test_end_to_end_withdrawal_flow(self, client, mock_external_services):
        """Test complete withdrawal workflow"""
        mock_get, mock_post = mock_external_services
        
        # Mock agent response
        with patch('app.services.agent.tier_allocation_agent.allocate_tiers') as mock_allocate:
            mock_allocate.return_value = TierAllocation(
                tier1=2000.0,
                tier2=1500.0,
                tier3=1500.0
            )
            
            # Step 1: Make withdrawal allocation request
            request_data = {
                "uuid": str(uuid.uuid4()),
                "accountid": "test-account-456",
                "amount": 5000.0,
                "purpose": "WITHDRAW"
            }
            
            response = client.post("/api/v1/allocation/allocate-tiers", json=request_data)
            
            # Step 2: Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "allocation" in data
            assert data["allocation"]["tier1"] == 2000.0
            assert data["allocation"]["tier2"] == 1500.0
            assert data["allocation"]["tier3"] == 1500.0
            
            # Step 3: Verify tier sum equals total amount
            allocation = data["allocation"]
            tier_sum = allocation["tier1"] + allocation["tier2"] + allocation["tier3"]
            assert abs(tier_sum - request_data["amount"]) < 0.01
            
            # Step 4: Verify successful response
            # Note: External service calls are bypassed when agent is mocked
            # In real E2E tests, we would verify external service calls
    
    def test_end_to_end_new_user_scenario(self, client, mock_external_services):
        """Test workflow for new user with no transaction history"""
        mock_get, mock_post = mock_external_services
        
        # Mock empty transaction history
        mock_get.return_value.json.return_value = {"transactions": []}
        
        # Mock agent failure (simulating new user scenario)
        with patch('app.services.agent.tier_allocation_agent.allocate_tiers') as mock_allocate:
            mock_allocate.side_effect = Exception("No transaction history")
            
            with patch('app.services.agent.tier_allocation_agent.get_default_allocation') as mock_default:
                mock_default.return_value = TierAllocation(
                    tier1=1000.0,  # 20% of 5000
                    tier2=1500.0,  # 30% of 5000
                    tier3=2500.0   # 50% of 5000
                )
                
                # Step 1: Make allocation request for new user
                request_data = {
                    "uuid": str(uuid.uuid4()),
                    "accountid": "new-user-123",
                    "amount": 5000.0,
                    "purpose": "INVEST"
                }
                
                response = client.post("/api/v1/allocation/allocate-tiers", json=request_data)
                
                # Step 2: Verify response uses default allocation
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "Default tier allocation used due to agent failure" in data["reasoning"]
                
                # Step 3: Verify default allocation percentages
                allocation = data["allocation"]
                assert allocation["tier1"] == 1000.0  # 20%
                assert allocation["tier2"] == 1500.0  # 30%
                assert allocation["tier3"] == 2500.0  # 50%
    
    def test_end_to_end_error_scenarios(self, client):
        """Test error scenarios in end-to-end workflow"""
        
        # Scenario 1: Invalid request data
        invalid_request = {
            "uuid": "invalid-uuid",
            "accountid": "",
            "amount": -1000.0,
            "purpose": "INVALID"
        }
        
        response = client.post("/api/v1/allocation/allocate-tiers", json=invalid_request)
        assert response.status_code == 422  # FastAPI returns 422 for validation errors
        
        # Scenario 2: External service failure
        with patch('httpx.get') as mock_get:
            mock_get.side_effect = httpx.ConnectError("Service unavailable")
            
            request_data = {
                "uuid": str(uuid.uuid4()),
                "accountid": "test-account-123",
                "amount": 10000.0,
                "purpose": "INVEST"
            }
            
            # Should fall back to default allocation
            with patch('app.services.agent.tier_allocation_agent.get_default_allocation') as mock_default:
                mock_default.return_value = TierAllocation(
                    tier1=2000.0,
                    tier2=3000.0,
                    tier3=5000.0
                )
                
                response = client.post("/api/v1/allocation/allocate-tiers", json=request_data)
                assert response.status_code == 200
                data = response.json()
                assert "Default tier allocation used due to agent failure" in data["reasoning"]
        
        # Scenario 3: Agent timeout
        with patch('app.services.agent.tier_allocation_agent.allocate_tiers') as mock_allocate:
            mock_allocate.side_effect = Exception("Agent timeout")
            
            with patch('app.services.agent.tier_allocation_agent.get_default_allocation') as mock_default:
                mock_default.return_value = TierAllocation(
                    tier1=1000.0,
                    tier2=1500.0,
                    tier3=2500.0
                )
                
                request_data = {
                    "uuid": str(uuid.uuid4()),
                    "accountid": "test-account-123",
                    "amount": 5000.0,
                    "purpose": "INVEST"
                }
                
                response = client.post("/api/v1/allocation/allocate-tiers", json=request_data)
                assert response.status_code == 200
                data = response.json()
                assert "Default tier allocation used due to agent failure" in data["reasoning"]
    
    def test_end_to_end_concurrent_requests(self, client, mock_external_services):
        """Test handling concurrent requests"""
        import threading
        import time
        
        mock_get, mock_post = mock_external_services
        
        # Mock agent response
        with patch('app.services.agent.tier_allocation_agent.allocate_tiers') as mock_allocate:
            mock_allocate.return_value = TierAllocation(
                tier1=1000.0,
                tier2=2000.0,
                tier3=7000.0
            )
            
            results = []
            
            def make_request():
                request_data = {
                    "uuid": str(uuid.uuid4()),
                    "accountid": "test-account-123",
                    "amount": 10000.0,
                    "purpose": "INVEST"
                }
                
                response = client.post("/api/v1/allocation/allocate-tiers", json=request_data)
                results.append(response.status_code)
            
            # Create multiple threads
            threads = []
            for _ in range(10):
                thread = threading.Thread(target=make_request)
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            # All requests should succeed
            assert all(status == 200 for status in results)
            assert len(results) == 10
    
    def test_end_to_end_service_dependencies(self, client):
        """Test service dependency handling"""
        
        # Test health check when all dependencies are healthy
        with patch('app.core.health.HealthChecker.check_health') as mock_health:
            mock_health.return_value = {
                "status": "healthy",
                "dependencies": [
                    {"name": "ledger-db", "status": "healthy"},
                    {"name": "queue-db", "status": "healthy"},
                    {"name": "portfolio-db", "status": "healthy"},
                    {"name": "gemini-api", "status": "healthy"}
                ]
            }
            
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
        
        # Test health check when dependencies are unhealthy
        with patch('app.core.health.HealthChecker.check_health') as mock_health:
            mock_health.return_value = {
                "status": "unhealthy",
                "dependencies": [
                    {"name": "ledger-db", "status": "unhealthy"},
                    {"name": "queue-db", "status": "healthy"},
                    {"name": "portfolio-db", "status": "healthy"},
                    {"name": "gemini-api", "status": "healthy"}
                ]
            }
            
            response = client.get("/health")
            assert response.status_code == 503
        
        # Test readiness check
        with patch('app.core.health.HealthChecker.check_readiness') as mock_readiness:
            mock_readiness.return_value = {
                "ready": True,
                "dependencies": [
                    {"name": "ledger-db", "status": "healthy"},
                    {"name": "queue-db", "status": "healthy"}
                ]
            }
            
            response = client.get("/ready")
            assert response.status_code == 200
            data = response.json()
            assert data["ready"] is True
    
    def test_end_to_end_metrics_and_monitoring(self, client):
        """Test metrics and monitoring endpoints"""
        
        # Test metrics endpoint
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        assert "http_requests_total" in response.text
        
        # Make some requests to generate metrics
        for _ in range(5):
            request_data = {
                "uuid": str(uuid.uuid4()),
                "accountid": "test-account-123",
                "amount": 1000.0,
                "purpose": "INVEST"
            }
            
            with patch('app.services.agent.tier_allocation_agent.allocate_tiers') as mock_allocate:
                mock_allocate.return_value = TierAllocation(
                    tier1=200.0,
                    tier2=300.0,
                    tier3=500.0
                )
                
                client.post("/api/v1/allocation/allocate-tiers", json=request_data)
        
        # Check metrics again
        response = client.get("/metrics")
        assert response.status_code == 200
        # Should have more requests now
        assert "http_requests_total" in response.text
    
    def test_end_to_end_request_id_propagation(self, client, mock_external_services):
        """Test request ID propagation through the system"""
        mock_get, mock_post = mock_external_services
        
        # Mock agent response
        with patch('app.services.agent.tier_allocation_agent.allocate_tiers') as mock_allocate:
            mock_allocate.return_value = TierAllocation(
                tier1=1000.0,
                tier2=2000.0,
                tier3=7000.0
            )
            
            # Custom request ID
            custom_request_id = "e2e-test-request-123"
            
            request_data = {
                "uuid": str(uuid.uuid4()),
                "accountid": "test-account-123",
                "amount": 10000.0,
                "purpose": "INVEST"
            }
            
            response = client.post(
                "/api/v1/allocation/allocate-tiers",
                json=request_data,
                headers={"X-Request-ID": custom_request_id}
            )
            
            # Verify request ID in response
            assert response.status_code == 200
            assert response.headers["X-Request-ID"] == custom_request_id
            
            data = response.json()
            assert data["request_id"] == custom_request_id
    
    def test_end_to_end_performance_characteristics(self, client, mock_external_services):
        """Test performance characteristics"""
        mock_get, mock_post = mock_external_services
        
        # Mock agent response
        with patch('app.services.agent.tier_allocation_agent.allocate_tiers') as mock_allocate:
            mock_allocate.return_value = TierAllocation(
                tier1=1000.0,
                tier2=2000.0,
                tier3=7000.0
            )
            
            request_data = {
                "uuid": str(uuid.uuid4()),
                "accountid": "test-account-123",
                "amount": 10000.0,
                "purpose": "INVEST"
            }
            
            # Measure response time
            start_time = time.time()
            response = client.post("/api/v1/allocation/allocate-tiers", json=request_data)
            end_time = time.time()
            
            response_time = end_time - start_time
            
            # Verify response
            assert response.status_code == 200
            
            # Performance assertion (should respond within 5 seconds)
            assert response_time < 5.0, f"Response time {response_time:.2f}s exceeded 5s limit"
            
            # Test multiple requests for consistency
            response_times = []
            for _ in range(10):
                start_time = time.time()
                response = client.post("/api/v1/allocation/allocate-tiers", json=request_data)
                end_time = time.time()
                
                assert response.status_code == 200
                response_times.append(end_time - start_time)
            
            # Average response time should be reasonable
            avg_response_time = sum(response_times) / len(response_times)
            assert avg_response_time < 3.0, f"Average response time {avg_response_time:.2f}s exceeded 3s limit"
