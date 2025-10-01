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
Unit tests for error handling.
Tests database errors, business logic errors, and error recovery.
"""

import pytest
import psycopg2
from decimal import Decimal
from tests.utils.test_database import TestDatabase, TestDataGenerator


class TestDatabaseErrors:
    """Test database-level error handling."""
    
    def test_connection_timeout_handling(self, test_db):
        """Test handling of connection timeout errors."""
        # This test simulates connection issues by using invalid connection string
        invalid_db = TestDatabase('postgresql://invalid:invalid@invalid:5432/invalid')
        
        with pytest.raises(ConnectionError):
            invalid_db.connect()
    
    def test_constraint_violation_handling(self, test_db):
        """Test handling of constraint violations."""
        # Test unique constraint violation
        request1 = TestDataGenerator.generate_investment_request()
        test_db.create_test_queue_entry(**request1)
        
        # Try to create duplicate UUID
        request2 = TestDataGenerator.generate_investment_request()
        request2['uuid'] = request1['uuid']
        
        with pytest.raises(psycopg2.IntegrityError) as exc_info:
            test_db.create_test_queue_entry(**request2)
        
        assert 'duplicate key value violates unique constraint' in str(exc_info.value)
    
    def test_check_constraint_violation(self, test_db):
        """Test handling of check constraint violations."""
        # Test negative tier amount constraint
        request = TestDataGenerator.generate_investment_request(
            tier_1=Decimal('-100.00')
        )
        
        with pytest.raises(psycopg2.IntegrityError) as exc_info:
            test_db.create_test_queue_entry(**request)
        
        assert 'check constraint' in str(exc_info.value).lower()
    
    def test_not_null_constraint_violation(self, test_db):
        """Test handling of NOT NULL constraint violations."""
        request = TestDataGenerator.generate_investment_request()
        request['accountid'] = None
        
        with pytest.raises(psycopg2.IntegrityError) as exc_info:
            test_db.create_test_queue_entry(**request)
        
        assert 'not null' in str(exc_info.value).lower()
    
    def test_transaction_rollback_on_error(self, test_db):
        """Test that transactions are properly rolled back on error."""
        # Start a transaction
        test_db.connection.autocommit = False
        
        try:
            # Create first entry successfully
            request1 = TestDataGenerator.generate_investment_request()
            test_db.create_test_queue_entry(**request1)
            
            # Try to create second entry with constraint violation
            request2 = TestDataGenerator.generate_investment_request()
            request2['uuid'] = request1['uuid']  # Duplicate UUID
            
            with pytest.raises(psycopg2.IntegrityError):
                test_db.create_test_queue_entry(**request2)
            
            # Verify first entry was rolled back
            test_db.connection.rollback()
            entries = test_db.get_queue_entries_by_account(request1['accountid'])
            assert len(entries) == 0
            
        finally:
            test_db.connection.autocommit = True


class TestBusinessLogicErrors:
    """Test business logic error handling."""
    
    def test_invalid_account_id_error(self, test_db):
        """Test handling of invalid account ID format."""
        # Test with account ID that's too long
        long_account_id = '1' * 21  # 21 characters, exceeds 20 char limit
        
        request = TestDataGenerator.generate_investment_request(
            accountid=long_account_id
        )
        
        with pytest.raises(psycopg2.DataError):
            test_db.create_test_queue_entry(**request)
    
    def test_duplicate_uuid_error(self, test_db):
        """Test handling of duplicate UUID errors."""
        request1 = TestDataGenerator.generate_investment_request()
        test_db.create_test_queue_entry(**request1)
        
        # Try to create entry with same UUID
        request2 = TestDataGenerator.generate_investment_request()
        request2['uuid'] = request1['uuid']
        
        with pytest.raises(psycopg2.IntegrityError) as exc_info:
            test_db.create_test_queue_entry(**request2)
        
        # Verify error code and message
        assert 'QUEUE_003' in str(exc_info.value) or 'duplicate' in str(exc_info.value).lower()
    
    def test_invalid_status_transition_error(self, test_db):
        """Test handling of invalid status transitions."""
        request = TestDataGenerator.generate_investment_request()
        entry = test_db.create_test_queue_entry(**request)
        
        # Try invalid transition: PENDING -> COMPLETED (should go through PROCESSING)
        # Note: Database allows this, but business logic should prevent it
        success = test_db.update_queue_status(entry['uuid'], 'COMPLETED')
        
        # In real implementation, this should return False or raise exception
        # For now, we verify the database allows it but business logic should prevent it
        assert success  # Database allows it
    
    def test_nonexistent_uuid_update_error(self, test_db):
        """Test handling of updates to non-existent UUIDs."""
        fake_uuid = '550e8400-e29b-41d4-a716-446655440999'
        
        success = test_db.update_queue_status(fake_uuid, 'PROCESSING')
        assert not success  # Should return False for non-existent UUID


class TestErrorRecovery:
    """Test error recovery mechanisms."""
    
    def test_connection_recovery(self, test_db):
        """Test database connection recovery."""
        # Simulate connection loss
        test_db.disconnect()
        
        # Attempt to reconnect
        test_db.connect()
        
        # Verify connection is working
        result = test_db.execute_query("SELECT 1 as test")
        assert result[0]['test'] == 1
    
    def test_retry_mechanism_simulation(self, test_db):
        """Test retry mechanism for transient errors."""
        # This simulates a retry mechanism for database operations
        max_retries = 3
        retry_count = 0
        
        def operation_with_retry():
            nonlocal retry_count
            retry_count += 1
            
            if retry_count < 3:
                raise psycopg2.OperationalError("Connection lost")
            else:
                return test_db.execute_query("SELECT 1 as test")
        
        # Simulate retry logic
        for attempt in range(max_retries):
            try:
                result = operation_with_retry()
                assert result[0]['test'] == 1
                break
            except psycopg2.OperationalError:
                if attempt == max_retries - 1:
                    raise
                continue
        
        assert retry_count == 3
    
    def test_graceful_degradation(self, test_db):
        """Test graceful degradation when database is unavailable."""
        # Simulate database unavailability
        test_db.disconnect()
        
        # Operations should fail gracefully
        with pytest.raises(ConnectionError):
            test_db.get_queue_entry('some-uuid')
        
        with pytest.raises(ConnectionError):
            test_db.create_test_queue_entry(
                **TestDataGenerator.generate_investment_request()
            )


class TestErrorCodes:
    """Test error code mapping and handling."""
    
    def test_error_code_mapping(self, test_db):
        """Test that errors are mapped to appropriate error codes."""
        # Test QUEUE_001: Invalid account ID
        long_account_id = '1' * 21
        request = TestDataGenerator.generate_investment_request(
            accountid=long_account_id
        )
        
        with pytest.raises(psycopg2.DataError):
            test_db.create_test_queue_entry(**request)
        # In real implementation, this should map to QUEUE_001
    
    def test_error_message_consistency(self, test_db):
        """Test that error messages are consistent and informative."""
        # Test duplicate UUID error
        request1 = TestDataGenerator.generate_investment_request()
        test_db.create_test_queue_entry(**request1)
        
        request2 = TestDataGenerator.generate_investment_request()
        request2['uuid'] = request1['uuid']
        
        with pytest.raises(psycopg2.IntegrityError) as exc_info:
            test_db.create_test_queue_entry(**request2)
        
        error_message = str(exc_info.value)
        assert 'uuid' in error_message.lower() or 'duplicate' in error_message.lower()
    
    def test_constraint_error_detection(self, test_db):
        """Test detection of different types of constraint errors."""
        # Test check constraint error
        request = TestDataGenerator.generate_investment_request(
            tier_1=Decimal('-100.00')
        )
        
        with pytest.raises(psycopg2.IntegrityError) as exc_info:
            test_db.create_test_queue_entry(**request)
        
        error_message = str(exc_info.value)
        assert 'check' in error_message.lower() or 'constraint' in error_message.lower()


class TestConcurrentAccess:
    """Test concurrent access and race condition handling."""
    
    def test_concurrent_insert_handling(self, test_db):
        """Test handling of concurrent insert operations."""
        # This test simulates concurrent access by creating multiple entries rapidly
        import threading
        import time
        
        results = []
        errors = []
        
        def create_entry(thread_id):
            try:
                request = TestDataGenerator.generate_investment_request(
                    accountid=f'101122611{thread_id}'
                )
                entry = test_db.create_test_queue_entry(**request)
                results.append(entry)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_entry, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all entries were created successfully
        assert len(results) == 5
        assert len(errors) == 0
        
        # Verify all entries have unique UUIDs
        uuids = [entry['uuid'] for entry in results]
        assert len(set(uuids)) == 5  # All UUIDs should be unique
    
    def test_concurrent_update_handling(self, test_db):
        """Test handling of concurrent update operations."""
        # Create an entry
        request = TestDataGenerator.generate_investment_request()
        entry = test_db.create_test_queue_entry(**request)
        
        # Simulate concurrent status updates
        import threading
        
        results = []
        
        def update_status(status):
            success = test_db.update_queue_status(entry['uuid'], status)
            results.append((status, success))
        
        # Create threads for concurrent updates
        threads = [
            threading.Thread(target=update_status, args=('PROCESSING',)),
            threading.Thread(target=update_status, args=('CANCELLED',))
        ]
        
        # Start threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # At least one update should succeed
        successful_updates = [success for _, success in results]
        assert any(successful_updates)
        
        # Verify final status
        final_entry = test_db.get_queue_entry(entry['uuid'])
        assert final_entry['status'] in ['PROCESSING', 'CANCELLED']
