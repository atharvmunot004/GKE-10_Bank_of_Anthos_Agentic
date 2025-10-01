# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Integration tests for end-to-end queue operations.
Tests complete workflows from request creation to processing completion.
"""

import pytest
import time
from decimal import Decimal
from tests.utils.test_database import TestDatabase, TestDataGenerator, assert_queue_entry_valid


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows."""
    
    def test_investment_request_complete_workflow(self, test_db):
        """Test complete investment request workflow from creation to completion."""
        # 1. Create investment request
        request = TestDataGenerator.generate_investment_request(
            accountid='1011226111',
            tier_1=Decimal('1000.00'),
            tier_2=Decimal('2000.00'),
            tier_3=Decimal('500.00')
        )
        
        entry = test_db.create_test_queue_entry(**request)
        assert entry['status'] == 'PENDING'
        assert entry['transaction_type'] == 'INVEST'
        
        # 2. Move to processing
        success = test_db.update_queue_status(entry['uuid'], 'PROCESSING')
        assert success
        
        updated_entry = test_db.get_queue_entry(entry['uuid'])
        assert updated_entry['status'] == 'PROCESSING'
        assert updated_entry['updated_at'] > updated_entry['created_at']
        
        # 3. Complete processing
        success = test_db.update_queue_status(entry['uuid'], 'COMPLETED')
        assert success
        
        final_entry = test_db.get_queue_entry(entry['uuid'])
        assert final_entry['status'] == 'COMPLETED'
        assert final_entry['processed_at'] is not None
        assert final_entry['processed_at'] >= final_entry['updated_at']
    
    def test_withdrawal_request_complete_workflow(self, test_db):
        """Test complete withdrawal request workflow from creation to completion."""
        # 1. Create withdrawal request
        request = TestDataGenerator.generate_withdrawal_request(
            accountid='1011226111',
            tier_1=Decimal('500.00'),
            tier_2=Decimal('1000.00'),
            tier_3=Decimal('250.00')
        )
        
        entry = test_db.create_test_queue_entry(**request)
        assert entry['status'] == 'PENDING'
        assert entry['transaction_type'] == 'WITHDRAW'
        
        # 2. Move to processing
        success = test_db.update_queue_status(entry['uuid'], 'PROCESSING')
        assert success
        
        # 3. Complete processing
        success = test_db.update_queue_status(entry['uuid'], 'COMPLETED')
        assert success
        
        final_entry = test_db.get_queue_entry(entry['uuid'])
        assert final_entry['status'] == 'COMPLETED'
        assert final_entry['processed_at'] is not None
    
    def test_failed_request_workflow(self, test_db):
        """Test failed request workflow with retry capability."""
        # 1. Create request
        request = TestDataGenerator.generate_investment_request()
        entry = test_db.create_test_queue_entry(**request)
        
        # 2. Move to processing
        test_db.update_queue_status(entry['uuid'], 'PROCESSING')
        
        # 3. Mark as failed
        success = test_db.update_queue_status(entry['uuid'], 'FAILED')
        assert success
        
        failed_entry = test_db.get_queue_entry(entry['uuid'])
        assert failed_entry['status'] == 'FAILED'
        assert failed_entry['processed_at'] is not None
        
        # 4. Retry by moving back to pending
        success = test_db.update_queue_status(entry['uuid'], 'PENDING')
        assert success
        
        retry_entry = test_db.get_queue_entry(entry['uuid'])
        assert retry_entry['status'] == 'PENDING'
        # processed_at should be cleared or remain as is (depending on implementation)
    
    def test_cancelled_request_workflow(self, test_db):
        """Test cancelled request workflow."""
        # 1. Create request
        request = TestDataGenerator.generate_investment_request()
        entry = test_db.create_test_queue_entry(**request)
        
        # 2. Cancel request
        success = test_db.update_queue_status(entry['uuid'], 'CANCELLED')
        assert success
        
        cancelled_entry = test_db.get_queue_entry(entry['uuid'])
        assert cancelled_entry['status'] == 'CANCELLED'
        # Cancelled requests typically don't have processed_at timestamp
    
    def test_multiple_account_workflow(self, test_db):
        """Test workflow with multiple accounts."""
        accounts = ['1011226111', '1011226112', '1011226113']
        
        # Create requests for each account
        entries = []
        for account_id in accounts:
            request = TestDataGenerator.generate_investment_request(accountid=account_id)
            entry = test_db.create_test_queue_entry(**request)
            entries.append(entry)
        
        # Process each request
        for entry in entries:
            test_db.update_queue_status(entry['uuid'], 'PROCESSING')
            test_db.update_queue_status(entry['uuid'], 'COMPLETED')
        
        # Verify all accounts have completed requests
        for account_id in accounts:
            account_entries = test_db.get_queue_entries_by_account(account_id)
            assert len(account_entries) == 1
            assert account_entries[0]['status'] == 'COMPLETED'


class TestDataConsistency:
    """Test data consistency across operations."""
    
    def test_transaction_rollback_consistency(self, test_db):
        """Test that failed transactions maintain data consistency."""
        # Start transaction
        test_db.connection.autocommit = False
        
        try:
            # Create first entry
            request1 = TestDataGenerator.generate_investment_request()
            entry1 = test_db.create_test_queue_entry(**request1)
            
            # Create second entry with duplicate UUID (should fail)
            request2 = TestDataGenerator.generate_investment_request()
            request2['uuid'] = entry1['uuid']
            
            with pytest.raises(Exception):
                test_db.create_test_queue_entry(**request2)
            
            # Rollback transaction
            test_db.connection.rollback()
            
            # Verify first entry was rolled back
            entries = test_db.get_queue_entries_by_account(request1['accountid'])
            assert len(entries) == 0
            
        finally:
            test_db.connection.autocommit = True
    
    def test_concurrent_operations_consistency(self, test_db):
        """Test data consistency under concurrent operations."""
        import threading
        import time
        
        results = []
        
        def create_and_process_request(thread_id):
            try:
                # Create request
                request = TestDataGenerator.generate_investment_request(
                    accountid=f'101122611{thread_id}'
                )
                entry = test_db.create_test_queue_entry(**request)
                
                # Process request
                test_db.update_queue_status(entry['uuid'], 'PROCESSING')
                time.sleep(0.1)  # Simulate processing time
                test_db.update_queue_status(entry['uuid'], 'COMPLETED')
                
                results.append(entry['uuid'])
            except Exception as e:
                results.append(f"Error: {e}")
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_and_process_request, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify all operations completed successfully
        assert len(results) == 5
        for result in results:
            assert not result.startswith("Error")
        
        # Verify all entries are in COMPLETED status
        for uuid in results:
            entry = test_db.get_queue_entry(uuid)
            assert entry['status'] == 'COMPLETED'
    
    def test_statistics_consistency(self, test_db):
        """Test that statistics remain consistent after operations."""
        # Create various entries
        test_data = [
            ('INVEST', 'PENDING'),
            ('INVEST', 'PROCESSING'),
            ('INVEST', 'COMPLETED'),
            ('WITHDRAW', 'PENDING'),
            ('WITHDRAW', 'FAILED'),
        ]
        
        created_entries = []
        for transaction_type, status in test_data:
            request = TestDataGenerator.generate_investment_request(
                transaction_type=transaction_type,
                status=status
            )
            entry = test_db.create_test_queue_entry(**request)
            created_entries.append(entry)
        
        # Get initial statistics
        initial_stats = test_db.get_queue_statistics()
        
        # Process one of the pending entries
        pending_entry = next(
            entry for entry in created_entries 
            if entry['status'] == 'PENDING'
        )
        
        test_db.update_queue_status(pending_entry['uuid'], 'PROCESSING')
        test_db.update_queue_status(pending_entry['uuid'], 'COMPLETED')
        
        # Get updated statistics
        updated_stats = test_db.get_queue_statistics()
        
        # Verify statistics changed appropriately
        assert updated_stats['COMPLETED_INVEST']['count'] > initial_stats['COMPLETED_INVEST']['count']
        assert updated_stats['PENDING_INVEST']['count'] < initial_stats['PENDING_INVEST']['count']


class TestPerformanceUnderLoad:
    """Test performance under load conditions."""
    
    def test_bulk_insert_performance(self, test_db):
        """Test performance of bulk insert operations."""
        start_time = time.time()
        
        # Create 100 entries
        entries = []
        for i in range(100):
            request = TestDataGenerator.generate_investment_request(
                accountid=f'101122611{i % 10}'  # 10 different accounts
            )
            entry = test_db.create_test_queue_entry(**request)
            entries.append(entry)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert duration < 10.0, f"Bulk insert took too long: {duration:.2f} seconds"
        
        # Verify all entries were created
        assert len(entries) == 100
        
        # Verify all entries are valid
        for entry in entries:
            assert_queue_entry_valid(entry)
    
    def test_concurrent_read_write_performance(self, test_db):
        """Test performance under concurrent read/write operations."""
        import threading
        import time
        
        read_results = []
        write_results = []
        
        def write_operations():
            start_time = time.time()
            for i in range(20):
                request = TestDataGenerator.generate_investment_request(
                    accountid=f'101122611{i % 5}'
                )
                entry = test_db.create_test_queue_entry(**request)
                write_results.append(entry['uuid'])
            end_time = time.time()
            write_results.append(f"Write duration: {end_time - start_time:.2f}s")
        
        def read_operations():
            start_time = time.time()
            for i in range(20):
                # Read statistics
                stats = test_db.get_queue_statistics()
                read_results.append(len(stats))
            end_time = time.time()
            read_results.append(f"Read duration: {end_time - start_time:.2f}s")
        
        # Start concurrent threads
        write_thread = threading.Thread(target=write_operations)
        read_thread = threading.Thread(target=read_operations)
        
        start_time = time.time()
        write_thread.start()
        read_thread.start()
        
        write_thread.join()
        read_thread.join()
        end_time = time.time()
        
        total_duration = end_time - start_time
        
        # Should complete within reasonable time
        assert total_duration < 15.0, f"Concurrent operations took too long: {total_duration:.2f} seconds"
        
        # Verify operations completed
        assert len([r for r in write_results if isinstance(r, str) and r.startswith("Write")]) == 1
        assert len([r for r in read_results if isinstance(r, str) and r.startswith("Read")]) == 1
    
    def test_query_performance(self, test_db):
        """Test query performance with large dataset."""
        # Create test data
        for i in range(50):
            request = TestDataGenerator.generate_investment_request(
                accountid=f'101122611{i % 10}',
                status=['PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'][i % 4]
            )
            test_db.create_test_queue_entry(**request)
        
        # Test various query performance
        queries = [
            "SELECT * FROM investment_withdrawal_queue WHERE status = 'PENDING'",
            "SELECT * FROM investment_withdrawal_queue WHERE accountid = '1011226111'",
            "SELECT * FROM queue_statistics",
            "SELECT * FROM account_queue_summary",
        ]
        
        for query in queries:
            start_time = time.time()
            result = test_db.execute_query(query)
            end_time = time.time()
            
            duration = end_time - start_time
            assert duration < 1.0, f"Query took too long: {duration:.2f} seconds for query: {query}"
            assert len(result) > 0, f"Query returned no results: {query}"


class TestDatabaseConnectionPooling:
    """Test database connection pooling and resource management."""
    
    def test_connection_reuse(self, test_db):
        """Test that connections are properly reused."""
        # Perform multiple operations to test connection reuse
        for i in range(10):
            request = TestDataGenerator.generate_investment_request()
            entry = test_db.create_test_queue_entry(**request)
            
            # Verify connection is still working
            retrieved_entry = test_db.get_queue_entry(entry['uuid'])
            assert retrieved_entry is not None
            assert retrieved_entry['uuid'] == entry['uuid']
    
    def test_connection_cleanup(self, test_db):
        """Test that connections are properly cleaned up."""
        # Create multiple database instances
        db_instances = []
        for i in range(5):
            db = TestDatabase()
            db.connect()
            db_instances.append(db)
        
        # Perform operations
        for db in db_instances:
            request = TestDataGenerator.generate_investment_request()
            db.create_test_queue_entry(**request)
        
        # Clean up all connections
        for db in db_instances:
            db.disconnect()
        
        # Verify connections are closed
        for db in db_instances:
            assert db.connection is None or db.connection.closed
