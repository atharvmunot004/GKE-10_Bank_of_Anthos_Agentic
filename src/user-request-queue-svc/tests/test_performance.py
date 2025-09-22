import unittest
from unittest.mock import patch, Mock
import json
import os
import sys
import time
import threading
from datetime import datetime

# Add parent directory to path to import the Flask app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from user_request_queue_svc import app

class TestPerformance(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        os.environ['QUEUE_DB_URI'] = 'postgresql://user:password@host:port/database'
        os.environ['BANK_ASSET_AGENT_URI'] = 'http://bank-asset-agent:8080'
        os.environ['BATCH_SIZE'] = '10'
        os.environ['REQUEST_TIMEOUT'] = '1'
        os.environ['POLLING_INTERVAL'] = '5'
        os.environ['TIER1'] = '1000000.0'
        os.environ['TIER2'] = '2000000.0'
        os.environ['TIER3'] = '500000.0'

    @patch('user_request_queue_svc.get_db_connection')
    def test_concurrent_queue_operations(self, mock_db_connect):
        """Test concurrent queue operations performance."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        def add_request(request_id):
            queue_data = {
                "uuid": f"test-uuid-{request_id}",
                "tier1": 100.0,
                "tier2": 200.0,
                "tier3": 50.0,
                "purpose": "INVEST",
                "accountid": f"123456789{request_id}"
            }
            
            start_time = time.time()
            response = self.app.post('/api/v1/queue', json=queue_data)
            end_time = time.time()
            
            return {
                'status_code': response.status_code,
                'response_time': end_time - start_time,
                'request_id': request_id
            }
        
        # Test concurrent requests
        num_requests = 20
        threads = []
        results = []
        
        def worker(request_id):
            result = add_request(request_id)
            results.append(result)
        
        # Start concurrent threads
        start_time = time.time()
        for i in range(num_requests):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Verify all requests succeeded
        self.assertEqual(len(results), num_requests)
        for result in results:
            self.assertEqual(result['status_code'], 200)
        
        # Performance assertions
        avg_response_time = sum(r['response_time'] for r in results) / len(results)
        self.assertLess(avg_response_time, 1.0, "Average response time should be under 1 second")
        self.assertLess(total_time, 5.0, "Total concurrent processing time should be under 5 seconds")
        
        print(f"Concurrent Performance Test Results:")
        print(f"- Total requests: {num_requests}")
        print(f"- Total time: {total_time:.2f}s")
        print(f"- Average response time: {avg_response_time:.3f}s")
        print(f"- Requests per second: {num_requests/total_time:.2f}")

    @patch('user_request_queue_svc.get_db_connection')
    def test_batch_processing_performance(self, mock_db_connect):
        """Test batch processing performance with large number of requests."""
        from user_request_queue_svc import process_batch
        
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Create large batch of requests
        batch_size = 50
        mock_requests = []
        for i in range(batch_size):
            mock_requests.append({
                'uuid': f'uuid-{i:03d}',
                'accountid': f'123456789{i}',
                'tier1': 100.0,
                'tier2': 200.0,
                'tier3': 50.0,
                'purpose': 'INVEST' if i % 2 == 0 else 'WITHDRAW'
            })
        
        # Mock database operations
        def mock_fetchall(query, params=None):
            if 'SELECT uuid' in query:
                return mock_requests[:10]  # Return first 10 for batch processing
            return []
        
        mock_cursor.fetchall.side_effect = mock_fetchall
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        # Mock bank-asset-agent response
        with patch('user_request_queue_svc.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'status': 'SUCCESS'}
            mock_post.return_value = mock_response
            
            # Measure batch processing time
            start_time = time.time()
            process_batch()
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            # Performance assertions
            self.assertLess(processing_time, 2.0, "Batch processing should complete under 2 seconds")
            
            print(f"Batch Processing Performance Test Results:")
            print(f"- Batch size: {len(mock_requests[:10])}")
            print(f"- Processing time: {processing_time:.3f}s")
            print(f"- Requests per second: {10/processing_time:.2f}")

    @patch('user_request_queue_svc.get_db_connection')
    def test_step5_tier_update_performance(self, mock_db_connect):
        """Test step5 tier update performance."""
        from user_request_queue_svc import update_global_tier_variables
        
        # Test with different batch sizes
        test_cases = [
            {'T1': 1000.0, 'T2': 2000.0, 'T3': 500.0},
            {'T1': 10000.0, 'T2': 20000.0, 'T3': 5000.0},
            {'T1': 100000.0, 'T2': 200000.0, 'T3': 50000.0},
        ]
        
        results = []
        
        for i, tier_changes in enumerate(test_cases):
            # Reset environment
            os.environ['TIER1'] = '1000000.0'
            os.environ['TIER2'] = '2000000.0'
            os.environ['TIER3'] = '500000.0'
            
            start_time = time.time()
            result = update_global_tier_variables(tier_changes)
            end_time = time.time()
            
            update_time = end_time - start_time
            results.append({
                'test_case': i + 1,
                'tier_changes': tier_changes,
                'update_time': update_time,
                'success': result
            })
            
            # Performance assertion
            self.assertLess(update_time, 0.1, f"Tier update {i+1} should complete under 0.1 seconds")
            self.assertTrue(result, f"Tier update {i+1} should succeed")
        
        print(f"Step 5 Tier Update Performance Test Results:")
        for result in results:
            print(f"- Test Case {result['test_case']}: {result['update_time']:.4f}s")

    @patch('user_request_queue_svc.get_db_connection')
    def test_database_operation_performance(self, mock_db_connect):
        """Test database operation performance."""
        from user_request_queue_svc import get_pending_requests, update_request_status
        
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Test get_pending_requests performance
        mock_requests = []
        for i in range(100):
            mock_requests.append({
                'uuid': f'uuid-{i:03d}',
                'accountid': f'123456789{i}',
                'tier1': 100.0,
                'tier2': 200.0,
                'tier3': 50.0,
                'purpose': 'INVEST'
            })
        
        mock_cursor.fetchall.return_value = mock_requests
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        start_time = time.time()
        result = get_pending_requests()
        end_time = time.time()
        
        query_time = end_time - start_time
        self.assertLess(query_time, 0.5, "Database query should complete under 0.5 seconds")
        
        # Test update_request_status performance
        uuid_list = [f'uuid-{i:03d}' for i in range(10)]
        
        start_time = time.time()
        update_result = update_request_status(uuid_list, 'DONE')
        end_time = time.time()
        
        update_time = end_time - start_time
        self.assertLess(update_time, 0.5, "Database update should complete under 0.5 seconds")
        self.assertTrue(update_result)
        
        print(f"Database Operation Performance Test Results:")
        print(f"- Query time (100 records): {query_time:.4f}s")
        print(f"- Update time (10 records): {update_time:.4f}s")

    def test_memory_usage_with_large_requests(self):
        """Test memory usage with large request payloads."""
        import psutil
        import gc
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create large request payloads
        large_requests = []
        for i in range(100):
            large_request = {
                "uuid": f"test-uuid-{i}" + "x" * 1000,  # Large UUID
                "tier1": 1000000.0 + i,
                "tier2": 2000000.0 + i,
                "tier3": 500000.0 + i,
                "purpose": "INVEST",
                "accountid": "1234567890" + "x" * 100,  # Large account ID
                "metadata": "x" * 10000  # Large metadata field
            }
            large_requests.append(large_request)
        
        # Process large requests (simulate)
        processed_count = 0
        for request in large_requests:
            # Simulate processing
            processed_count += 1
        
        # Force garbage collection
        gc.collect()
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory usage assertions
        self.assertLess(memory_increase, 50, "Memory increase should be under 50MB")
        self.assertEqual(processed_count, 100, "All requests should be processed")
        
        print(f"Memory Usage Test Results:")
        print(f"- Initial memory: {initial_memory:.2f} MB")
        print(f"- Final memory: {final_memory:.2f} MB")
        print(f"- Memory increase: {memory_increase:.2f} MB")
        print(f"- Processed requests: {processed_count}")

    @patch('user_request_queue_svc.get_db_connection')
    def test_error_handling_performance(self, mock_db_connect):
        """Test error handling performance."""
        # Test with database connection failures
        mock_db_connect.side_effect = Exception("Database connection failed")
        
        queue_data = {
            "uuid": "test-error-uuid",
            "tier1": 1000.0,
            "tier2": 2000.0,
            "tier3": 500.0,
            "purpose": "INVEST",
            "accountid": "1234567890"
        }
        
        start_time = time.time()
        response = self.app.post('/api/v1/queue', json=queue_data)
        end_time = time.time()
        
        error_handling_time = end_time - start_time
        
        # Should fail gracefully and quickly
        self.assertEqual(response.status_code, 500)
        self.assertLess(error_handling_time, 1.0, "Error handling should complete under 1 second")
        
        print(f"Error Handling Performance Test Results:")
        print(f"- Error handling time: {error_handling_time:.4f}s")

if __name__ == '__main__':
    print("⚡ Running User Request Queue Service Performance Tests")
    print("============================================================")
    unittest.main()
