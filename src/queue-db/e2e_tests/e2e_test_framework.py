#!/usr/bin/env python3
"""
End-to-End Testing Framework for Queue-DB Microservice
This framework provides tools for E2E testing including API simulation,
workflow testing, and cross-service integration testing.
"""

import psycopg2
import psycopg2.extras
import uuid
import time
import json
import requests
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

class QueueDBE2ETestFramework:
    """End-to-End testing framework for Queue-DB microservice."""
    
    def __init__(self, db_connection_string: str, api_base_url: str = None):
        self.db_connection_string = db_connection_string
        self.api_base_url = api_base_url or "http://localhost:8080"  # Future API endpoint
        self.test_results = []
        self.test_data_cleanup = []
    
    def log_result(self, test_name: str, passed: bool, message: str = "", details: Dict = None):
        """Log test result with details."""
        status = "✅ PASSED" if passed else "❌ FAILED"
        result = {
            'test': test_name,
            'status': status,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        self.test_results.append(result)
        print(f"{status}: {test_name} - {message}")
    
    def get_db_connection(self):
        """Get database connection."""
        return psycopg2.connect(self.db_connection_string)
    
    def cleanup_test_data(self):
        """Clean up all test data created during tests."""
        if not self.test_data_cleanup:
            return
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            for cleanup_query, params in self.test_data_cleanup:
                cursor.execute(cleanup_query, params)
            conn.commit()
            print(f"🧹 Cleaned up {len(self.test_data_cleanup)} test data entries")
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")
        finally:
            cursor.close()
            conn.close()
            self.test_data_cleanup.clear()
    
    def create_test_request(self, account_id: str, transaction_type: str, 
                           tier_amounts: Dict[str, Decimal], expected_status: str = "PENDING") -> str:
        """Create a test request and return UUID."""
        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            test_uuid = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO investment_withdrawal_queue 
                (accountid, tier_1, tier_2, tier_3, uuid, transaction_type, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            ''', (account_id, tier_amounts['tier_1'], tier_amounts['tier_2'], 
                  tier_amounts['tier_3'], test_uuid, transaction_type, expected_status))
            
            result = cursor.fetchone()
            conn.commit()
            
            # Add to cleanup list
            self.test_data_cleanup.append(
                ("DELETE FROM investment_withdrawal_queue WHERE uuid = %s", (test_uuid,))
            )
            
            return test_uuid
        finally:
            cursor.close()
            conn.close()
    
    def simulate_api_request(self, endpoint: str, method: str = "GET", data: Dict = None) -> Dict:
        """Simulate API request (for future API integration)."""
        # This is a placeholder for when the API layer is implemented
        # For now, we'll simulate the API behavior using direct database operations
        
        if endpoint.startswith("/queue/investment") and method == "POST":
            return self._simulate_create_investment_request(data)
        elif endpoint.startswith("/queue/withdrawal") and method == "POST":
            return self._simulate_create_withdrawal_request(data)
        elif endpoint.startswith("/queue/") and method == "GET":
            return self._simulate_get_request(endpoint)
        elif endpoint.startswith("/queue/") and method == "PUT":
            return self._simulate_update_request(endpoint, data)
        else:
            return {"error": "Endpoint not implemented", "status_code": 404}
    
    def _simulate_create_investment_request(self, data: Dict) -> Dict:
        """Simulate POST /queue/investment API call."""
        try:
            test_uuid = self.create_test_request(
                account_id=data['accountid'],
                transaction_type='INVEST',
                tier_amounts={
                    'tier_1': Decimal(str(data['tier_1'])),
                    'tier_2': Decimal(str(data['tier_2'])),
                    'tier_3': Decimal(str(data['tier_3']))
                }
            )
            return {
                "status_code": 201,
                "data": {"uuid": test_uuid, "status": "PENDING"},
                "message": "Investment request created successfully"
            }
        except Exception as e:
            return {"status_code": 400, "error": str(e)}
    
    def _simulate_create_withdrawal_request(self, data: Dict) -> Dict:
        """Simulate POST /queue/withdrawal API call."""
        try:
            test_uuid = self.create_test_request(
                account_id=data['accountid'],
                transaction_type='WITHDRAW',
                tier_amounts={
                    'tier_1': Decimal(str(data['tier_1'])),
                    'tier_2': Decimal(str(data['tier_2'])),
                    'tier_3': Decimal(str(data['tier_3']))
                }
            )
            return {
                "status_code": 201,
                "data": {"uuid": test_uuid, "status": "PENDING"},
                "message": "Withdrawal request created successfully"
            }
        except Exception as e:
            return {"status_code": 400, "error": str(e)}
    
    def _simulate_get_request(self, endpoint: str) -> Dict:
        """Simulate GET request to queue endpoint."""
        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            if "/queue/" in endpoint and len(endpoint.split("/")) >= 3:
                uuid_param = endpoint.split("/")[-1]
                cursor.execute('SELECT * FROM investment_withdrawal_queue WHERE uuid = %s', (uuid_param,))
                result = cursor.fetchone()
                
                if result:
                    return {
                        "status_code": 200,
                        "data": dict(result),
                        "message": "Request found"
                    }
                else:
                    return {"status_code": 404, "error": "Request not found"}
            else:
                return {"status_code": 400, "error": "Invalid endpoint"}
        finally:
            cursor.close()
            conn.close()
    
    def _simulate_update_request(self, endpoint: str, data: Dict) -> Dict:
        """Simulate PUT request to update queue status."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            uuid_param = endpoint.split("/")[-2]  # Extract UUID from /queue/{uuid}/status
            new_status = data.get('status')
            
            cursor.execute('UPDATE investment_withdrawal_queue SET status = %s WHERE uuid = %s', 
                          (new_status, uuid_param))
            
            if cursor.rowcount > 0:
                conn.commit()
                return {
                    "status_code": 200,
                    "data": {"uuid": uuid_param, "status": new_status},
                    "message": "Status updated successfully"
                }
            else:
                return {"status_code": 404, "error": "Request not found"}
        finally:
            cursor.close()
            conn.close()

class QueueDBE2ETests:
    """End-to-End test scenarios for Queue-DB microservice."""
    
    def __init__(self, framework: QueueDBE2ETestFramework):
        self.framework = framework
    
    def test_complete_investment_journey(self):
        """Test complete investment journey from API request to completion."""
        print("\n🌟 E2E Test: Complete Investment Journey")
        
        # Step 1: Create investment request via API simulation
        api_data = {
            'accountid': '1011226111',
            'tier_1': 1000.50,
            'tier_2': 2000.75,
            'tier_3': 500.25
        }
        
        response = self.framework.simulate_api_request("/queue/investment", "POST", api_data)
        
        if response.get('status_code') != 201:
            self.framework.log_result("Investment Journey - Creation", False, 
                                    f"API creation failed: {response}")
            return
        
        request_uuid = response['data']['uuid']
        
        # Step 2: Verify request was created
        get_response = self.framework.simulate_api_request(f"/queue/{request_uuid}", "GET")
        
        if get_response.get('status_code') != 200:
            self.framework.log_result("Investment Journey - Verification", False, 
                                    "Request verification failed")
            return
        
        # Step 3: Process the request through workflow
        # Move to PROCESSING
        update_response = self.framework.simulate_api_request(
            f"/queue/{request_uuid}/status", "PUT", {"status": "PROCESSING"}
        )
        
        if update_response.get('status_code') != 200:
            self.framework.log_result("Investment Journey - Processing", False, 
                                    "Status update to PROCESSING failed")
            return
        
        # Move to COMPLETED
        complete_response = self.framework.simulate_api_request(
            f"/queue/{request_uuid}/status", "PUT", {"status": "COMPLETED"}
        )
        
        if complete_response.get('status_code') != 200:
            self.framework.log_result("Investment Journey - Completion", False, 
                                    "Status update to COMPLETED failed")
            return
        
        # Step 4: Verify final state
        final_response = self.framework.simulate_api_request(f"/queue/{request_uuid}", "GET")
        
        if (final_response.get('status_code') == 200 and 
            final_response['data']['status'] == 'COMPLETED'):
            self.framework.log_result("Complete Investment Journey", True, 
                                    "Full workflow completed successfully")
        else:
            self.framework.log_result("Complete Investment Journey", False, 
                                    "Final verification failed")
    
    def test_complete_withdrawal_journey(self):
        """Test complete withdrawal journey from API request to completion."""
        print("\n🌟 E2E Test: Complete Withdrawal Journey")
        
        # Similar to investment journey but for withdrawals
        api_data = {
            'accountid': '1011226111',
            'tier_1': 500.00,
            'tier_2': 1000.00,
            'tier_3': 250.00
        }
        
        response = self.framework.simulate_api_request("/queue/withdrawal", "POST", api_data)
        
        if response.get('status_code') != 201:
            self.framework.log_result("Withdrawal Journey", False, 
                                    f"API creation failed: {response}")
            return
        
        request_uuid = response['data']['uuid']
        
        # Process through workflow
        self.framework.simulate_api_request(f"/queue/{request_uuid}/status", "PUT", {"status": "PROCESSING"})
        self.framework.simulate_api_request(f"/queue/{request_uuid}/status", "PUT", {"status": "COMPLETED"})
        
        # Verify final state
        final_response = self.framework.simulate_api_request(f"/queue/{request_uuid}", "GET")
        
        if (final_response.get('status_code') == 200 and 
            final_response['data']['status'] == 'COMPLETED' and
            final_response['data']['transaction_type'] == 'WITHDRAW'):
            self.framework.log_result("Complete Withdrawal Journey", True, 
                                    "Full workflow completed successfully")
        else:
            self.framework.log_result("Complete Withdrawal Journey", False, 
                                    "Final verification failed")
    
    def test_error_handling_journey(self):
        """Test error handling and recovery journey."""
        print("\n🌟 E2E Test: Error Handling Journey")
        
        # Create request
        api_data = {
            'accountid': '1011226111',
            'tier_1': 1000.00,
            'tier_2': 2000.00,
            'tier_3': 500.00
        }
        
        response = self.framework.simulate_api_request("/queue/investment", "POST", api_data)
        request_uuid = response['data']['uuid']
        
        # Simulate failure
        self.framework.simulate_api_request(f"/queue/{request_uuid}/status", "PUT", {"status": "PROCESSING"})
        self.framework.simulate_api_request(f"/queue/{request_uuid}/status", "PUT", {"status": "FAILED"})
        
        # Retry
        self.framework.simulate_api_request(f"/queue/{request_uuid}/status", "PUT", {"status": "PENDING"})
        self.framework.simulate_api_request(f"/queue/{request_uuid}/status", "PUT", {"status": "PROCESSING"})
        self.framework.simulate_api_request(f"/queue/{request_uuid}/status", "PUT", {"status": "COMPLETED"})
        
        # Verify recovery
        final_response = self.framework.simulate_api_request(f"/queue/{request_uuid}", "GET")
        
        if (final_response.get('status_code') == 200 and 
            final_response['data']['status'] == 'COMPLETED'):
            self.framework.log_result("Error Handling Journey", True, 
                                    "Error recovery workflow successful")
        else:
            self.framework.log_result("Error Handling Journey", False, 
                                    "Error recovery failed")
    
    def test_multi_account_scenario(self):
        """Test multi-account scenario with concurrent operations."""
        print("\n🌟 E2E Test: Multi-Account Scenario")
        
        accounts = ['1011226111', '1011226112', '1011226113']
        created_requests = []
        
        # Create requests for multiple accounts
        for account in accounts:
            # Investment request
            inv_response = self.framework.simulate_api_request("/queue/investment", "POST", {
                'accountid': account,
                'tier_1': 1000.00,
                'tier_2': 2000.00,
                'tier_3': 500.00
            })
            
            # Withdrawal request
            with_response = self.framework.simulate_api_request("/queue/withdrawal", "POST", {
                'accountid': account,
                'tier_1': 500.00,
                'tier_2': 1000.00,
                'tier_3': 250.00
            })
            
            if inv_response.get('status_code') == 201 and with_response.get('status_code') == 201:
                created_requests.extend([inv_response['data']['uuid'], with_response['data']['uuid']])
        
        # Process all requests
        for request_uuid in created_requests:
            self.framework.simulate_api_request(f"/queue/{request_uuid}/status", "PUT", {"status": "PROCESSING"})
            self.framework.simulate_api_request(f"/queue/{request_uuid}/status", "PUT", {"status": "COMPLETED"})
        
        # Verify all completed
        completed_count = 0
        for request_uuid in created_requests:
            response = self.framework.simulate_api_request(f"/queue/{request_uuid}", "GET")
            if response.get('status_code') == 200 and response['data']['status'] == 'COMPLETED':
                completed_count += 1
        
        if completed_count == len(created_requests):
            self.framework.log_result("Multi-Account Scenario", True, 
                                    f"Processed {completed_count} requests across {len(accounts)} accounts")
        else:
            self.framework.log_result("Multi-Account Scenario", False, 
                                    f"Only {completed_count}/{len(created_requests)} requests completed")
    
    def run_all_e2e_tests(self):
        """Run all E2E tests."""
        print("🚀 Starting Queue-DB End-to-End Tests...\n")
        
        try:
            self.test_complete_investment_journey()
            self.test_complete_withdrawal_journey()
            self.test_error_handling_journey()
            self.test_multi_account_scenario()
        finally:
            # Always cleanup test data
            self.framework.cleanup_test_data()
        
        # Print summary
        print("\n" + "="*60)
        print("🎯 END-TO-END TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for result in self.framework.test_results if "✅" in result['status'])
        total = len(self.framework.test_results)
        
        for result in self.framework.test_results:
            print(f"{result['status']}: {result['test']}")
        
        print(f"\n📊 Results: {passed}/{total} E2E tests passed")
        
        if passed == total:
            print("🎉 All E2E tests PASSED!")
        else:
            print(f"⚠️  {total - passed} E2E tests FAILED")
        
        return passed == total

if __name__ == "__main__":
    # Initialize framework
    framework = QueueDBE2ETestFramework(
        db_connection_string="postgresql://queue-admin:queue-pwd@localhost:5432/queue-db"
    )
    
    # Run E2E tests
    e2e_tests = QueueDBE2ETests(framework)
    success = e2e_tests.run_all_e2e_tests()
    
    exit(0 if success else 1)
