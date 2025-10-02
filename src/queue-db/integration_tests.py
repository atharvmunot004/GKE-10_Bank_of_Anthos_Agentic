#!/usr/bin/env python3
"""
Integration Tests for Queue-DB Microservice
Tests end-to-end workflows and integration scenarios
"""

import psycopg2
import psycopg2.extras
import uuid
import time
import threading
from decimal import Decimal
from datetime import datetime, timezone

class QueueDBIntegrationTests:
    def __init__(self):
        self.connection_string = "postgresql://queue-admin:queue-pwd@localhost:5432/queue-db"
        self.test_results = []
    
    def get_connection(self):
        """Get database connection."""
        return psycopg2.connect(self.connection_string)
    
    def log_result(self, test_name, passed, message=""):
        """Log test result."""
        status = "✅ PASSED" if passed else "❌ FAILED"
        self.test_results.append({
            'test': test_name,
            'status': status,
            'message': message
        })
        print(f"{status}: {test_name} - {message}")
    
    def test_end_to_end_investment_workflow(self):
        """Test complete investment workflow from creation to completion."""
        print("\n🔄 Test: End-to-End Investment Workflow")
        
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            # Step 1: Create investment request
            test_uuid = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO investment_withdrawal_queue 
                (accountid, tier_1, tier_2, tier_3, uuid, transaction_type, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            ''', ('1011226111', Decimal('1000.00'), Decimal('2000.00'), Decimal('500.00'), test_uuid, 'INVEST', 'PENDING'))
            
            entry = cursor.fetchone()
            if not entry or entry['status'] != 'PENDING':
                self.log_result("E2E Investment - Creation", False, "Failed to create investment request")
                return
            
            # Step 2: Move to processing
            cursor.execute('UPDATE investment_withdrawal_queue SET status = %s WHERE uuid = %s', ('PROCESSING', test_uuid))
            
            # Step 3: Complete processing
            cursor.execute('UPDATE investment_withdrawal_queue SET status = %s WHERE uuid = %s', ('COMPLETED', test_uuid))
            
            # Step 4: Verify final state
            cursor.execute('SELECT * FROM investment_withdrawal_queue WHERE uuid = %s', (test_uuid,))
            final_entry = cursor.fetchone()
            
            if final_entry and final_entry['status'] == 'COMPLETED':
                self.log_result("E2E Investment Workflow", True, "Complete workflow successful")
            else:
                self.log_result("E2E Investment Workflow", False, "Workflow completion failed")
            
            # Cleanup
            cursor.execute('DELETE FROM investment_withdrawal_queue WHERE uuid = %s', (test_uuid,))
            conn.commit()
            
        except Exception as e:
            self.log_result("E2E Investment Workflow", False, f"Exception: {str(e)}")
        finally:
            cursor.close()
            conn.close()
    
    def test_end_to_end_withdrawal_workflow(self):
        """Test complete withdrawal workflow from creation to completion."""
        print("\n🔄 Test: End-to-End Withdrawal Workflow")
        
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            # Create withdrawal request
            test_uuid = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO investment_withdrawal_queue 
                (accountid, tier_1, tier_2, tier_3, uuid, transaction_type, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            ''', ('1011226111', Decimal('500.00'), Decimal('1000.00'), Decimal('250.00'), test_uuid, 'WITHDRAW', 'PENDING'))
            
            # Process through workflow
            cursor.execute('UPDATE investment_withdrawal_queue SET status = %s WHERE uuid = %s', ('PROCESSING', test_uuid))
            cursor.execute('UPDATE investment_withdrawal_queue SET status = %s WHERE uuid = %s', ('COMPLETED', test_uuid))
            
            # Verify
            cursor.execute('SELECT * FROM investment_withdrawal_queue WHERE uuid = %s', (test_uuid,))
            final_entry = cursor.fetchone()
            
            if final_entry and final_entry['status'] == 'COMPLETED' and final_entry['transaction_type'] == 'WITHDRAW':
                self.log_result("E2E Withdrawal Workflow", True, "Complete workflow successful")
            else:
                self.log_result("E2E Withdrawal Workflow", False, "Workflow completion failed")
            
            # Cleanup
            cursor.execute('DELETE FROM investment_withdrawal_queue WHERE uuid = %s', (test_uuid,))
            conn.commit()
            
        except Exception as e:
            self.log_result("E2E Withdrawal Workflow", False, f"Exception: {str(e)}")
        finally:
            cursor.close()
            conn.close()
    
    def test_failed_request_retry_workflow(self):
        """Test failed request retry workflow."""
        print("\n🔄 Test: Failed Request Retry Workflow")
        
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            # Create request
            test_uuid = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO investment_withdrawal_queue 
                (accountid, tier_1, tier_2, tier_3, uuid, transaction_type, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', ('1011226111', Decimal('1000.00'), Decimal('2000.00'), Decimal('500.00'), test_uuid, 'INVEST', 'PENDING'))
            
            # Move to processing then fail
            cursor.execute('UPDATE investment_withdrawal_queue SET status = %s WHERE uuid = %s', ('PROCESSING', test_uuid))
            cursor.execute('UPDATE investment_withdrawal_queue SET status = %s WHERE uuid = %s', ('FAILED', test_uuid))
            
            # Retry by moving back to pending
            cursor.execute('UPDATE investment_withdrawal_queue SET status = %s WHERE uuid = %s', ('PENDING', test_uuid))
            
            # Process again to completion
            cursor.execute('UPDATE investment_withdrawal_queue SET status = %s WHERE uuid = %s', ('PROCESSING', test_uuid))
            cursor.execute('UPDATE investment_withdrawal_queue SET status = %s WHERE uuid = %s', ('COMPLETED', test_uuid))
            
            # Verify final state
            cursor.execute('SELECT status FROM investment_withdrawal_queue WHERE uuid = %s', (test_uuid,))
            result = cursor.fetchone()
            
            if result and result['status'] == 'COMPLETED':
                self.log_result("Failed Request Retry", True, "Retry workflow successful")
            else:
                self.log_result("Failed Request Retry", False, "Retry workflow failed")
            
            # Cleanup
            cursor.execute('DELETE FROM investment_withdrawal_queue WHERE uuid = %s', (test_uuid,))
            conn.commit()
            
        except Exception as e:
            self.log_result("Failed Request Retry", False, f"Exception: {str(e)}")
        finally:
            cursor.close()
            conn.close()
    
    def test_concurrent_operations(self):
        """Test concurrent database operations."""
        print("\n🔄 Test: Concurrent Operations")
        
        def create_requests(thread_id, num_requests=5):
            """Create requests in a separate thread."""
            conn = self.get_connection()
            cursor = conn.cursor()
            created_uuids = []
            
            try:
                for i in range(num_requests):
                    test_uuid = str(uuid.uuid4())
                    created_uuids.append(test_uuid)
                    cursor.execute('''
                        INSERT INTO investment_withdrawal_queue 
                        (accountid, tier_1, tier_2, tier_3, uuid, transaction_type, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ''', (f'101122611{thread_id}', Decimal('100.00'), Decimal('200.00'), Decimal('50.00'), 
                          test_uuid, 'INVEST', 'PENDING'))
                
                conn.commit()
                return created_uuids
            except Exception as e:
                print(f"Thread {thread_id} error: {e}")
                return []
            finally:
                cursor.close()
                conn.close()
        
        # Run concurrent operations
        threads = []
        all_uuids = []
        
        for i in range(3):  # 3 concurrent threads
            thread = threading.Thread(target=lambda i=i: all_uuids.extend(create_requests(i)))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT COUNT(*) FROM investment_withdrawal_queue WHERE uuid = ANY(%s)', (all_uuids,))
            count = cursor.fetchone()[0]
            
            if count == 15:  # 3 threads * 5 requests each
                self.log_result("Concurrent Operations", True, f"Created {count} requests concurrently")
            else:
                self.log_result("Concurrent Operations", False, f"Expected 15, got {count} requests")
            
            # Cleanup
            if all_uuids:
                cursor.execute('DELETE FROM investment_withdrawal_queue WHERE uuid = ANY(%s)', (all_uuids,))
                conn.commit()
            
        except Exception as e:
            self.log_result("Concurrent Operations", False, f"Exception: {str(e)}")
        finally:
            cursor.close()
            conn.close()
    
    def test_data_consistency(self):
        """Test data consistency across operations."""
        print("\n🔄 Test: Data Consistency")
        
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            # Create multiple requests
            test_uuids = []
            for i in range(10):
                test_uuid = str(uuid.uuid4())
                test_uuids.append(test_uuid)
                transaction_type = 'INVEST' if i % 2 == 0 else 'WITHDRAW'
                cursor.execute('''
                    INSERT INTO investment_withdrawal_queue 
                    (accountid, tier_1, tier_2, tier_3, uuid, transaction_type, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', ('1011226111', Decimal('100.00'), Decimal('200.00'), Decimal('50.00'), 
                      test_uuid, transaction_type, 'PENDING'))
            
            # Update some to different statuses
            for i, uuid in enumerate(test_uuids[:5]):
                status = ['PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED', 'PENDING'][i]
                cursor.execute('UPDATE investment_withdrawal_queue SET status = %s WHERE uuid = %s', (status, uuid))
            
            # Verify counts
            cursor.execute('SELECT status, COUNT(*) FROM investment_withdrawal_queue WHERE uuid = ANY(%s) GROUP BY status', (test_uuids,))
            status_counts = dict(cursor.fetchall())
            
            expected_statuses = {'PENDING': 6, 'PROCESSING': 1, 'COMPLETED': 1, 'FAILED': 1, 'CANCELLED': 1}
            
            consistent = all(status_counts.get(status, 0) == count for status, count in expected_statuses.items())
            
            if consistent:
                self.log_result("Data Consistency", True, "Status counts match expected values")
            else:
                self.log_result("Data Consistency", False, f"Expected: {expected_statuses}, Got: {status_counts}")
            
            # Cleanup
            cursor.execute('DELETE FROM investment_withdrawal_queue WHERE uuid = ANY(%s)', (test_uuids,))
            conn.commit()
            
        except Exception as e:
            self.log_result("Data Consistency", False, f"Exception: {str(e)}")
        finally:
            cursor.close()
            conn.close()
    
    def test_performance_under_load(self):
        """Test performance under load."""
        print("\n🔄 Test: Performance Under Load")
        
        start_time = time.time()
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Create 100 requests rapidly
            test_uuids = []
            for i in range(100):
                test_uuid = str(uuid.uuid4())
                test_uuids.append(test_uuid)
                cursor.execute('''
                    INSERT INTO investment_withdrawal_queue 
                    (accountid, tier_1, tier_2, tier_3, uuid, transaction_type, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (f'101122611{i % 10}', Decimal('100.00'), Decimal('200.00'), Decimal('50.00'), 
                      test_uuid, 'INVEST', 'PENDING'))
            
            conn.commit()
            end_time = time.time()
            duration = end_time - start_time
            
            if duration < 5.0:  # Should complete within 5 seconds
                self.log_result("Performance Under Load", True, f"Created 100 requests in {duration:.2f} seconds")
            else:
                self.log_result("Performance Under Load", False, f"Too slow: {duration:.2f} seconds")
            
            # Cleanup
            cursor.execute('DELETE FROM investment_withdrawal_queue WHERE uuid = ANY(%s)', (test_uuids,))
            conn.commit()
            
        except Exception as e:
            self.log_result("Performance Under Load", False, f"Exception: {str(e)}")
        finally:
            cursor.close()
            conn.close()
    
    def run_all_tests(self):
        """Run all integration tests."""
        print("🚀 Starting Queue-DB Integration Tests...\n")
        
        # Run all test methods
        self.test_end_to_end_investment_workflow()
        self.test_end_to_end_withdrawal_workflow()
        self.test_failed_request_retry_workflow()
        self.test_concurrent_operations()
        self.test_data_consistency()
        self.test_performance_under_load()
        
        # Print summary
        print("\n" + "="*60)
        print("🎯 INTEGRATION TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for result in self.test_results if "✅" in result['status'])
        total = len(self.test_results)
        
        for result in self.test_results:
            print(f"{result['status']}: {result['test']}")
        
        print(f"\n📊 Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All integration tests PASSED!")
        else:
            print(f"⚠️  {total - passed} tests FAILED")
        
        return passed == total

if __name__ == "__main__":
    tester = QueueDBIntegrationTests()
    success = tester.run_all_tests()
    exit(0 if success else 1)
