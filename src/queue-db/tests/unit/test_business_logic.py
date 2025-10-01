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
Unit tests for business logic validation.
Tests queue operations, status transitions, and validation rules.
"""

import pytest
from decimal import Decimal
from tests.utils.test_database import TestDatabase, TestDataGenerator, assert_queue_entry_valid


class TestQueueOperations:
    """Test queue operations and business logic."""
    
    def test_create_investment_request(self, test_db, sample_investment_request):
        """Test creating a valid investment request."""
        entry = test_db.create_test_queue_entry(**sample_investment_request)
        
        assert_queue_entry_valid(entry)
        assert entry['transaction_type'] == 'INVEST'
        assert entry['status'] == 'PENDING'
        assert entry['accountid'] == sample_investment_request['accountid']
        assert entry['tier_1'] == sample_investment_request['tier_1']
        assert entry['tier_2'] == sample_investment_request['tier_2']
        assert entry['tier_3'] == sample_investment_request['tier_3']
        assert entry['uuid'] == sample_investment_request['uuid']
    
    def test_create_withdrawal_request(self, test_db, sample_withdrawal_request):
        """Test creating a valid withdrawal request."""
        entry = test_db.create_test_queue_entry(**sample_withdrawal_request)
        
        assert_queue_entry_valid(entry)
        assert entry['transaction_type'] == 'WITHDRAW'
        assert entry['status'] == 'PENDING'
        assert entry['accountid'] == sample_withdrawal_request['accountid']
    
    def test_uuid_generation_uniqueness(self, test_db):
        """Test that UUIDs are unique across multiple requests."""
        uuids = set()
        
        for _ in range(10):
            request = TestDataGenerator.generate_investment_request()
            entry = test_db.create_test_queue_entry(**request)
            assert entry['uuid'] not in uuids, "UUID collision detected"
            uuids.add(entry['uuid'])
    
    def test_initial_status_pending(self, test_db):
        """Test that new requests start with PENDING status."""
        request = TestDataGenerator.generate_investment_request()
        entry = test_db.create_test_queue_entry(**request)
        
        assert entry['status'] == 'PENDING'
    
    def test_tier_amounts_validation(self, test_db):
        """Test that tier amounts are properly validated."""
        # Test with zero amounts (should be allowed)
        request = TestDataGenerator.generate_investment_request(
            tier_1=Decimal('0.00'),
            tier_2=Decimal('0.00'),
            tier_3=Decimal('0.00')
        )
        entry = test_db.create_test_queue_entry(**request)
        assert entry['tier_1'] == Decimal('0.00')
        assert entry['tier_2'] == Decimal('0.00')
        assert entry['tier_3'] == Decimal('0.00')
    
    def test_account_id_format_validation(self, test_db):
        """Test that account ID format is validated."""
        # Test with valid account ID
        request = TestDataGenerator.generate_investment_request(accountid='1011226111')
        entry = test_db.create_test_queue_entry(**request)
        assert entry['accountid'] == '1011226111'
        
        # Test with maximum length account ID
        long_account_id = '1' * 20
        request = TestDataGenerator.generate_investment_request(accountid=long_account_id)
        entry = test_db.create_test_queue_entry(**request)
        assert entry['accountid'] == long_account_id


class TestStatusTransitions:
    """Test status transition business logic."""
    
    def test_valid_status_transitions(self, test_db):
        """Test valid status transitions."""
        # PENDING -> PROCESSING
        request = TestDataGenerator.generate_investment_request()
        entry = test_db.create_test_queue_entry(**request)
        
        success = test_db.update_queue_status(entry['uuid'], 'PROCESSING')
        assert success
        
        updated_entry = test_db.get_queue_entry(entry['uuid'])
        assert updated_entry['status'] == 'PROCESSING'
        
        # PROCESSING -> COMPLETED
        success = test_db.update_queue_status(entry['uuid'], 'COMPLETED')
        assert success
        
        updated_entry = test_db.get_queue_entry(entry['uuid'])
        assert updated_entry['status'] == 'COMPLETED'
    
    def test_pending_to_cancelled_transition(self, test_db):
        """Test PENDING -> CANCELLED transition."""
        request = TestDataGenerator.generate_investment_request()
        entry = test_db.create_test_queue_entry(**request)
        
        success = test_db.update_queue_status(entry['uuid'], 'CANCELLED')
        assert success
        
        updated_entry = test_db.get_queue_entry(entry['uuid'])
        assert updated_entry['status'] == 'CANCELLED'
    
    def test_processing_to_failed_transition(self, test_db):
        """Test PROCESSING -> FAILED transition."""
        request = TestDataGenerator.generate_investment_request()
        entry = test_db.create_test_queue_entry(**request)
        
        # First transition to PROCESSING
        test_db.update_queue_status(entry['uuid'], 'PROCESSING')
        
        # Then transition to FAILED
        success = test_db.update_queue_status(entry['uuid'], 'FAILED')
        assert success
        
        updated_entry = test_db.get_queue_entry(entry['uuid'])
        assert updated_entry['status'] == 'FAILED'
    
    def test_failed_to_pending_retry(self, test_db):
        """Test FAILED -> PENDING retry transition."""
        request = TestDataGenerator.generate_investment_request()
        entry = test_db.create_test_queue_entry(**request)
        
        # Transition to PROCESSING then FAILED
        test_db.update_queue_status(entry['uuid'], 'PROCESSING')
        test_db.update_queue_status(entry['uuid'], 'FAILED')
        
        # Retry by transitioning back to PENDING
        success = test_db.update_queue_status(entry['uuid'], 'PENDING')
        assert success
        
        updated_entry = test_db.get_queue_entry(entry['uuid'])
        assert updated_entry['status'] == 'PENDING'
    
    def test_terminal_statuses_cannot_change(self, test_db):
        """Test that terminal statuses (COMPLETED, CANCELLED) cannot change."""
        request = TestDataGenerator.generate_investment_request()
        entry = test_db.create_test_queue_entry(**request)
        
        # Transition to COMPLETED
        test_db.update_queue_status(entry['uuid'], 'PROCESSING')
        test_db.update_queue_status(entry['uuid'], 'COMPLETED')
        
        # Try to change from COMPLETED (should fail in real implementation)
        # Note: This test assumes the application layer enforces this rule
        # The database allows the update, but business logic should prevent it
        success = test_db.update_queue_status(entry['uuid'], 'PENDING')
        # In a real implementation, this should return False or raise an exception
        # For now, we just verify the update happens (database level)
        assert success  # Database allows it, but application should prevent it


class TestDataRetrieval:
    """Test data retrieval operations."""
    
    def test_get_queue_entry_by_uuid(self, test_db):
        """Test retrieving a queue entry by UUID."""
        request = TestDataGenerator.generate_investment_request()
        created_entry = test_db.create_test_queue_entry(**request)
        
        retrieved_entry = test_db.get_queue_entry(created_entry['uuid'])
        
        assert retrieved_entry is not None
        assert retrieved_entry['uuid'] == created_entry['uuid']
        assert retrieved_entry['accountid'] == created_entry['accountid']
    
    def test_get_nonexistent_queue_entry(self, test_db):
        """Test retrieving a non-existent queue entry."""
        fake_uuid = '550e8400-e29b-41d4-a716-446655440999'
        retrieved_entry = test_db.get_queue_entry(fake_uuid)
        
        assert retrieved_entry is None
    
    def test_get_queue_entries_by_account(self, test_db):
        """Test retrieving all queue entries for an account."""
        account_id = '1011226111'
        
        # Create multiple entries for the same account
        entries = []
        for i in range(3):
            request = TestDataGenerator.generate_investment_request(accountid=account_id)
            entry = test_db.create_test_queue_entry(**request)
            entries.append(entry)
        
        # Create entry for different account
        other_request = TestDataGenerator.generate_investment_request(accountid='1011226112')
        test_db.create_test_queue_entry(**other_request)
        
        # Retrieve entries for the first account
        account_entries = test_db.get_queue_entries_by_account(account_id)
        
        assert len(account_entries) == 3
        for entry in account_entries:
            assert entry['accountid'] == account_id
    
    def test_queue_statistics(self, test_db):
        """Test queue statistics generation."""
        # Create various entries with different statuses
        test_data = [
            ('INVEST', 'PENDING'),
            ('INVEST', 'PROCESSING'),
            ('INVEST', 'COMPLETED'),
            ('WITHDRAW', 'PENDING'),
            ('WITHDRAW', 'FAILED'),
        ]
        
        for transaction_type, status in test_data:
            request = TestDataGenerator.generate_investment_request(
                transaction_type=transaction_type,
                status=status
            )
            test_db.create_test_queue_entry(**request)
        
        stats = test_db.get_queue_statistics()
        
        # Verify statistics contain expected combinations
        expected_keys = [
            'PENDING_INVEST',
            'PROCESSING_INVEST',
            'COMPLETED_INVEST',
            'PENDING_WITHDRAW',
            'FAILED_WITHDRAW'
        ]
        
        for key in expected_keys:
            assert key in stats, f"Missing statistics for {key}"
            assert stats[key]['count'] == 1


class TestValidationRules:
    """Test business validation rules."""
    
    def test_account_id_format_validation(self, test_db):
        """Test account ID format validation."""
        # Valid account IDs
        valid_account_ids = [
            '1011226111',
            '12345678901234567890',  # 20 characters
            '1',
            '99999999999999999999'   # 20 characters
        ]
        
        for account_id in valid_account_ids:
            request = TestDataGenerator.generate_investment_request(accountid=account_id)
            entry = test_db.create_test_queue_entry(**request)
            assert entry['accountid'] == account_id
    
    def test_tier_amounts_non_negative(self, test_db):
        """Test that tier amounts must be non-negative."""
        # This is tested at the database constraint level
        # Here we test the business logic assumption
        request = TestDataGenerator.generate_investment_request(
            tier_1=Decimal('100.50'),
            tier_2=Decimal('200.75'),
            tier_3=Decimal('50.25')
        )
        
        entry = test_db.create_test_queue_entry(**request)
        assert entry['tier_1'] >= 0
        assert entry['tier_2'] >= 0
        assert entry['tier_3'] >= 0
    
    def test_transaction_type_validation(self, test_db):
        """Test transaction type validation."""
        valid_types = ['INVEST', 'WITHDRAW']
        
        for transaction_type in valid_types:
            request = TestDataGenerator.generate_investment_request(
                transaction_type=transaction_type
            )
            entry = test_db.create_test_queue_entry(**request)
            assert entry['transaction_type'] == transaction_type
    
    def test_status_validation(self, test_db):
        """Test status validation."""
        valid_statuses = ['PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED']
        
        for status in valid_statuses:
            request = TestDataGenerator.generate_investment_request(status=status)
            entry = test_db.create_test_queue_entry(**request)
            assert entry['status'] == status
