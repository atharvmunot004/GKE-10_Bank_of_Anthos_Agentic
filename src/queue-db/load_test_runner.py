#!/usr/bin/env python3
"""
Load Testing Runner for Queue-DB Microservice
Provides comprehensive load testing capabilities
"""

import psycopg2
import psycopg2.extras
import uuid
import time
import threading
import statistics
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple

class QueueDBLoadTester:
    """Load testing framework for Queue-DB microservice."""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.test_results = []
        self.performance_metrics = []
    
    def get_connection(self):
        """Get database connection."""
        return psycopg2.connect(self.connection_string)
    
    def create_request_load_test(self, num_requests: int, concurrent_threads: int = 10) -> Dict:
        """Test creating requests under load."""
        print(f"\n🔥 Load Test: Creating {num_requests} requests with {concurrent_threads} threads")
        
        start_time = time.time()
        created_uuids = []
        errors = []
        response_times = []
        
        def create_single_request(thread_id: int, request_id: int) -> Tuple[str, float, str]:
            """Create a single request and measure response time."""
            request_start = time.time()
            conn = None
            
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                test_uuid = str(uuid.uuid4())
                account_id = f"101122611{request_id % 100}"  # Distribute across 100 accounts
                transaction_type = 'INVEST' if request_id % 2 == 0 else 'WITHDRAW'
                
                cursor.execute('''
                    INSERT INTO investment_withdrawal_queue 
                    (accountid, tier_1, tier_2, tier_3, uuid, transaction_type, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (account_id, Decimal('100.00'), Decimal('200.00'), Decimal('50.00'), 
                      test_uuid, transaction_type, 'PENDING'))
                
                conn.commit()
                request_time = time.time() - request_start
                
                return test_uuid, request_time, None
                
            except Exception as e:
                request_time = time.time() - request_start
                return None, request_time, str(e)
            finally:
                if conn:
                    conn.close()
        
        # Execute load test with thread pool
        with ThreadPoolExecutor(max_workers=concurrent_threads) as executor:
            futures = []
            
            for i in range(num_requests):
                future = executor.submit(create_single_request, i % concurrent_threads, i)
                futures.append(future)
            
            # Collect results
            for future in as_completed(futures):
                test_uuid, response_time, error = future.result()
                response_times.append(response_time)
                
                if error:
                    errors.append(error)
                elif test_uuid:
                    created_uuids.append(test_uuid)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Calculate metrics
        success_rate = (len(created_uuids) / num_requests) * 100
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max(response_times)
        throughput = num_requests / total_duration
        
        results = {
            'test_name': 'Create Request Load Test',
            'num_requests': num_requests,
            'concurrent_threads': concurrent_threads,
            'total_duration': total_duration,
            'success_count': len(created_uuids),
            'error_count': len(errors),
            'success_rate': success_rate,
            'avg_response_time': avg_response_time,
            'p95_response_time': p95_response_time,
            'throughput': throughput,
            'created_uuids': created_uuids
        }
        
        print(f"✅ Created {len(created_uuids)}/{num_requests} requests")
        print(f"📊 Success Rate: {success_rate:.1f}%")
        print(f"⚡ Throughput: {throughput:.1f} requests/second")
        print(f"⏱️  Avg Response Time: {avg_response_time*1000:.1f}ms")
        print(f"📈 P95 Response Time: {p95_response_time*1000:.1f}ms")
        
        if errors:
            print(f"⚠️  Errors: {len(errors)}")
            for error in errors[:5]:  # Show first 5 errors
                print(f"   - {error}")
        
        return results
    
    def update_status_load_test(self, created_uuids: List[str], concurrent_threads: int = 10) -> Dict:
        """Test updating request statuses under load."""
        print(f"\n🔥 Load Test: Updating {len(created_uuids)} request statuses")
        
        if not created_uuids:
            return {'error': 'No UUIDs provided for status update test'}
        
        start_time = time.time()
        updated_count = 0
        errors = []
        response_times = []
        
        def update_single_status(uuid_to_update: str) -> Tuple[bool, float, str]:
            """Update a single request status."""
            update_start = time.time()
            conn = None
            
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                # Simulate workflow: PENDING -> PROCESSING -> COMPLETED
                cursor.execute('UPDATE investment_withdrawal_queue SET status = %s WHERE uuid = %s', 
                              ('PROCESSING', uuid_to_update))
                cursor.execute('UPDATE investment_withdrawal_queue SET status = %s WHERE uuid = %s', 
                              ('COMPLETED', uuid_to_update))
                
                conn.commit()
                update_time = time.time() - update_start
                
                return True, update_time, None
                
            except Exception as e:
                update_time = time.time() - update_start
                return False, update_time, str(e)
            finally:
                if conn:
                    conn.close()
        
        # Execute updates with thread pool
        with ThreadPoolExecutor(max_workers=concurrent_threads) as executor:
            futures = []
            
            for uuid_to_update in created_uuids:
                future = executor.submit(update_single_status, uuid_to_update)
                futures.append(future)
            
            # Collect results
            for future in as_completed(futures):
                success, response_time, error = future.result()
                response_times.append(response_time)
                
                if error:
                    errors.append(error)
                elif success:
                    updated_count += 1
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Calculate metrics
        success_rate = (updated_count / len(created_uuids)) * 100
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max(response_times)
        throughput = len(created_uuids) / total_duration
        
        results = {
            'test_name': 'Update Status Load Test',
            'num_updates': len(created_uuids),
            'concurrent_threads': concurrent_threads,
            'total_duration': total_duration,
            'success_count': updated_count,
            'error_count': len(errors),
            'success_rate': success_rate,
            'avg_response_time': avg_response_time,
            'p95_response_time': p95_response_time,
            'throughput': throughput
        }
        
        print(f"✅ Updated {updated_count}/{len(created_uuids)} requests")
        print(f"📊 Success Rate: {success_rate:.1f}%")
        print(f"⚡ Throughput: {throughput:.1f} updates/second")
        print(f"⏱️  Avg Response Time: {avg_response_time*1000:.1f}ms")
        print(f"📈 P95 Response Time: {p95_response_time*1000:.1f}ms")
        
        return results
    
    def query_load_test(self, num_queries: int, concurrent_threads: int = 10) -> Dict:
        """Test querying requests under load."""
        print(f"\n🔥 Load Test: Executing {num_queries} queries with {concurrent_threads} threads")
        
        start_time = time.time()
        successful_queries = 0
        errors = []
        response_times = []
        
        def execute_single_query(query_id: int) -> Tuple[bool, float, str]:
            """Execute a single query."""
            query_start = time.time()
            conn = None
            
            try:
                conn = self.get_connection()
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                # Mix of different query types
                query_type = query_id % 4
                
                if query_type == 0:
                    # Get all pending requests
                    cursor.execute("SELECT * FROM investment_withdrawal_queue WHERE status = 'PENDING' LIMIT 10")
                elif query_type == 1:
                    # Get requests by account
                    account_id = f"101122611{query_id % 100}"
                    cursor.execute("SELECT * FROM investment_withdrawal_queue WHERE accountid = %s LIMIT 10", (account_id,))
                elif query_type == 2:
                    # Get investment requests
                    cursor.execute("SELECT * FROM investment_withdrawal_queue WHERE transaction_type = 'INVEST' LIMIT 10")
                else:
                    # Count by status
                    cursor.execute("SELECT status, COUNT(*) FROM investment_withdrawal_queue GROUP BY status")
                
                results = cursor.fetchall()
                query_time = time.time() - query_start
                
                return True, query_time, None
                
            except Exception as e:
                query_time = time.time() - query_start
                return False, query_time, str(e)
            finally:
                if conn:
                    conn.close()
        
        # Execute queries with thread pool
        with ThreadPoolExecutor(max_workers=concurrent_threads) as executor:
            futures = []
            
            for i in range(num_queries):
                future = executor.submit(execute_single_query, i)
                futures.append(future)
            
            # Collect results
            for future in as_completed(futures):
                success, response_time, error = future.result()
                response_times.append(response_time)
                
                if error:
                    errors.append(error)
                elif success:
                    successful_queries += 1
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Calculate metrics
        success_rate = (successful_queries / num_queries) * 100
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max(response_times)
        throughput = num_queries / total_duration
        
        results = {
            'test_name': 'Query Load Test',
            'num_queries': num_queries,
            'concurrent_threads': concurrent_threads,
            'total_duration': total_duration,
            'success_count': successful_queries,
            'error_count': len(errors),
            'success_rate': success_rate,
            'avg_response_time': avg_response_time,
            'p95_response_time': p95_response_time,
            'throughput': throughput
        }
        
        print(f"✅ Executed {successful_queries}/{num_queries} queries")
        print(f"📊 Success Rate: {success_rate:.1f}%")
        print(f"⚡ Throughput: {throughput:.1f} queries/second")
        print(f"⏱️  Avg Response Time: {avg_response_time*1000:.1f}ms")
        print(f"📈 P95 Response Time: {p95_response_time*1000:.1f}ms")
        
        return results
    
    def cleanup_test_data(self, created_uuids: List[str]):
        """Clean up test data."""
        if not created_uuids:
            return
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM investment_withdrawal_queue WHERE uuid = ANY(%s)', (created_uuids,))
            deleted_count = cursor.rowcount
            conn.commit()
            print(f"🧹 Cleaned up {deleted_count} test records")
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")
        finally:
            cursor.close()
            conn.close()
    
    def run_comprehensive_load_test(self, num_requests: int = 1000, concurrent_threads: int = 20):
        """Run comprehensive load test suite."""
        print("🚀 Starting Comprehensive Load Testing...\n")
        print(f"📋 Test Configuration:")
        print(f"   - Requests: {num_requests}")
        print(f"   - Concurrent Threads: {concurrent_threads}")
        print(f"   - Database: {self.connection_string.split('@')[1] if '@' in self.connection_string else 'localhost'}")
        
        all_results = []
        created_uuids = []
        
        try:
            # Test 1: Create requests under load
            create_results = self.create_request_load_test(num_requests, concurrent_threads)
            all_results.append(create_results)
            created_uuids = create_results.get('created_uuids', [])
            
            # Test 2: Update statuses under load
            if created_uuids:
                update_results = self.update_status_load_test(created_uuids, concurrent_threads)
                all_results.append(update_results)
            
            # Test 3: Query under load
            query_results = self.query_load_test(num_requests // 2, concurrent_threads)
            all_results.append(query_results)
            
        finally:
            # Always cleanup
            if created_uuids:
                self.cleanup_test_data(created_uuids)
        
        # Print comprehensive summary
        print("\n" + "="*60)
        print("🎯 COMPREHENSIVE LOAD TEST SUMMARY")
        print("="*60)
        
        for result in all_results:
            if 'error' not in result:
                print(f"\n📊 {result['test_name']}:")
                print(f"   Success Rate: {result['success_rate']:.1f}%")
                print(f"   Throughput: {result['throughput']:.1f} ops/second")
                print(f"   Avg Response: {result['avg_response_time']*1000:.1f}ms")
                print(f"   P95 Response: {result['p95_response_time']*1000:.1f}ms")
        
        # Overall assessment
        overall_success = all(result.get('success_rate', 0) >= 95 for result in all_results if 'error' not in result)
        
        if overall_success:
            print("\n🎉 Load testing PASSED! System performs well under load.")
        else:
            print("\n⚠️ Load testing revealed performance issues.")
        
        return all_results

if __name__ == "__main__":
    # Initialize load tester
    load_tester = QueueDBLoadTester(
        connection_string="postgresql://queue-admin:queue-pwd@localhost:5432/queue-db"
    )
    
    # Run comprehensive load test
    results = load_tester.run_comprehensive_load_test(
        num_requests=500,  # Moderate load for testing
        concurrent_threads=10
    )
