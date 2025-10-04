"""
Locust load testing for User Tier Agent microservice
"""

import json
import random
import uuid
from locust import HttpUser, task, between
from locust.exception import RescheduleTask


class UserTierAgentUser(HttpUser):
    """Locust user for testing User Tier Agent microservice"""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Called when a user starts"""
        self.account_ids = [
            "account-001", "account-002", "account-003", "account-004", "account-005",
            "account-006", "account-007", "account-008", "account-009", "account-010"
        ]
        self.purposes = ["INVEST", "WITHDRAW"]
        self.amounts = [1000, 5000, 10000, 25000, 50000, 100000]
    
    @task(10)
    def allocate_tiers_invest(self):
        """Test tier allocation for investment requests"""
        request_data = {
            "uuid": str(uuid.uuid4()),
            "accountid": random.choice(self.account_ids),
            "amount": random.choice(self.amounts),
            "purpose": "INVEST"
        }
        
        with self.client.post(
            "/api/v1/allocation/allocate-tiers",
            json=request_data,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("success") and "allocation" in data:
                        # Validate allocation
                        allocation = data["allocation"]
                        tier_sum = allocation["tier1"] + allocation["tier2"] + allocation["tier3"]
                        if abs(tier_sum - request_data["amount"]) < 0.01:
                            response.success()
                        else:
                            response.failure(f"Invalid allocation: sum {tier_sum} != amount {request_data['amount']}")
                    else:
                        response.failure(f"Invalid response: {data}")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}: {response.text}")
    
    @task(5)
    def allocate_tiers_withdraw(self):
        """Test tier allocation for withdrawal requests"""
        request_data = {
            "uuid": str(uuid.uuid4()),
            "accountid": random.choice(self.account_ids),
            "amount": random.choice(self.amounts),
            "purpose": "WITHDRAW"
        }
        
        with self.client.post(
            "/api/v1/allocation/allocate-tiers",
            json=request_data,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("success") and "allocation" in data:
                        # Validate allocation
                        allocation = data["allocation"]
                        tier_sum = allocation["tier1"] + allocation["tier2"] + allocation["tier3"]
                        if abs(tier_sum - request_data["amount"]) < 0.01:
                            response.success()
                        else:
                            response.failure(f"Invalid allocation: sum {tier_sum} != amount {request_data['amount']}")
                    else:
                        response.failure(f"Invalid response: {data}")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}: {response.text}")
    
    @task(2)
    def get_default_allocation(self):
        """Test getting default allocation"""
        account_id = random.choice(self.account_ids)
        amount = random.choice(self.amounts)
        
        with self.client.get(
            f"/api/v1/allocation/allocate-tiers/{account_id}/default",
            params={"amount": amount},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("success") and "allocation" in data:
                        # Validate allocation
                        allocation = data["allocation"]
                        tier_sum = allocation["tier1"] + allocation["tier2"] + allocation["tier3"]
                        if abs(tier_sum - amount) < 0.01:
                            response.success()
                        else:
                            response.failure(f"Invalid allocation: sum {tier_sum} != amount {amount}")
                    else:
                        response.failure(f"Invalid response: {data}")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}: {response.text}")
    
    @task(1)
    def health_check(self):
        """Test health check endpoint"""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("status") == "healthy":
                        response.success()
                    else:
                        response.failure(f"Unhealthy status: {data}")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}: {response.text}")
    
    @task(1)
    def readiness_check(self):
        """Test readiness check endpoint"""
        with self.client.get("/ready", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("ready") is True:
                        response.success()
                    else:
                        response.failure(f"Not ready: {data}")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}: {response.text}")
    
    @task(1)
    def metrics_endpoint(self):
        """Test metrics endpoint"""
        with self.client.get("/metrics", catch_response=True) as response:
            if response.status_code == 200:
                if "http_requests_total" in response.text:
                    response.success()
                else:
                    response.failure("Metrics not found in response")
            else:
                response.failure(f"HTTP {response.status_code}: {response.text}")
    
    @task(1)
    def invalid_request_validation(self):
        """Test request validation with invalid data"""
        invalid_request_data = {
            "uuid": "invalid-uuid",
            "accountid": "",
            "amount": -1000.0,
            "purpose": "INVALID"
        }
        
        with self.client.post(
            "/api/v1/allocation/allocate-tiers",
            json=invalid_request_data,
            catch_response=True
        ) as response:
            if response.status_code == 400:
                response.success()
            else:
                response.failure(f"Expected 400, got {response.status_code}")


class HighLoadUser(HttpUser):
    """High load user for stress testing"""
    
    wait_time = between(0.1, 0.5)  # Very short wait time for high load
    
    def on_start(self):
        """Called when a user starts"""
        self.account_ids = [f"stress-account-{i:03d}" for i in range(100)]
        self.amounts = [1000, 5000, 10000, 25000, 50000]
    
    @task(20)
    def rapid_allocation_requests(self):
        """Rapid allocation requests for stress testing"""
        request_data = {
            "uuid": str(uuid.uuid4()),
            "accountid": random.choice(self.account_ids),
            "amount": random.choice(self.amounts),
            "purpose": random.choice(["INVEST", "WITHDRAW"])
        }
        
        with self.client.post(
            "/api/v1/allocation/allocate-tiers",
            json=request_data,
            catch_response=True
        ) as response:
            if response.status_code in [200, 503, 504]:  # Accept timeouts under stress
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(5)
    def health_check_under_load(self):
        """Health checks under load"""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")


class SpikeTestUser(HttpUser):
    """Spike test user for testing sudden load increases"""
    
    wait_time = between(0, 1)  # Variable wait time
    
    def on_start(self):
        """Called when a user starts"""
        self.account_ids = [f"spike-account-{i:02d}" for i in range(50)]
        self.amounts = [5000, 10000, 25000]
    
    @task(30)
    def spike_allocation_requests(self):
        """Spike allocation requests"""
        request_data = {
            "uuid": str(uuid.uuid4()),
            "accountid": random.choice(self.account_ids),
            "amount": random.choice(self.amounts),
            "purpose": "INVEST"
        }
        
        with self.client.post(
            "/api/v1/allocation/allocate-tiers",
            json=request_data,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("success"):
                        response.success()
                    else:
                        response.failure(f"Request failed: {data}")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code in [503, 504]:
                # Accept service unavailable during spikes
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(10)
    def spike_health_checks(self):
        """Health checks during spikes"""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code in [200, 503]:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")
