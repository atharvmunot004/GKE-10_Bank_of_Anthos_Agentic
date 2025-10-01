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
Unit tests for database schema validation.
Tests table structure, constraints, indexes, and triggers.
"""

import pytest
import psycopg2
from decimal import Decimal
from tests.utils.test_database import TestDatabase, TestDataGenerator


class TestSchemaValidation:
    """Test database schema validation."""
    
    def test_table_exists(self, test_db):
        """Test that the investment_withdrawal_queue table exists."""
        query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name = 'investment_withdrawal_queue'
        """
        result = test_db.execute_query(query)
        assert len(result) == 1
        assert result[0]['table_name'] == 'investment_withdrawal_queue'
    
    def test_table_columns(self, test_db):
        """Test that all required columns exist with correct types."""
        query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_name = 'investment_withdrawal_queue'
        ORDER BY ordinal_position
        """
        columns = test_db.execute_query(query)
        
        expected_columns = {
            'queue_id': {'data_type': 'integer', 'is_nullable': 'NO'},
            'accountid': {'data_type': 'character varying', 'is_nullable': 'NO'},
            'tier_1': {'data_type': 'numeric', 'is_nullable': 'NO'},
            'tier_2': {'data_type': 'numeric', 'is_nullable': 'NO'},
            'tier_3': {'data_type': 'numeric', 'is_nullable': 'NO'},
            'uuid': {'data_type': 'character varying', 'is_nullable': 'NO'},
            'transaction_type': {'data_type': 'character varying', 'is_nullable': 'NO'},
            'status': {'data_type': 'character varying', 'is_nullable': 'NO'},
            'created_at': {'data_type': 'timestamp with time zone', 'is_nullable': 'YES'},
            'updated_at': {'data_type': 'timestamp with time zone', 'is_nullable': 'YES'},
            'processed_at': {'data_type': 'timestamp with time zone', 'is_nullable': 'YES'}
        }
        
        assert len(columns) == len(expected_columns)
        
        for column in columns:
            column_name = column['column_name']
            assert column_name in expected_columns
            expected = expected_columns[column_name]
            assert column['data_type'] == expected['data_type']
            assert column['is_nullable'] == expected['is_nullable']
    
    def test_primary_key_constraint(self, test_db):
        """Test that queue_id is the primary key."""
        query = """
        SELECT column_name
        FROM information_schema.key_column_usage
        WHERE table_name = 'investment_withdrawal_queue' 
        AND constraint_name LIKE '%_pkey'
        """
        result = test_db.execute_query(query)
        assert len(result) == 1
        assert result[0]['column_name'] == 'queue_id'
    
    def test_unique_constraint_on_uuid(self, test_db):
        """Test that uuid column has unique constraint."""
        query = """
        SELECT column_name
        FROM information_schema.key_column_usage
        WHERE table_name = 'investment_withdrawal_queue' 
        AND column_name = 'uuid'
        """
        result = test_db.execute_query(query)
        assert len(result) >= 1  # Should have unique constraint
    
    def test_check_constraints(self, test_db):
        """Test that check constraints are properly defined."""
        query = """
        SELECT constraint_name, check_clause
        FROM information_schema.check_constraints
        WHERE constraint_name LIKE '%investment_withdrawal_queue%'
        """
        constraints = test_db.execute_query(query)
        
        constraint_clauses = [c['check_clause'] for c in constraints]
        
        # Check for transaction_type constraint
        transaction_type_constraint = any(
            "transaction_type IN ('INVEST', 'WITHDRAW')" in clause
            for clause in constraint_clauses
        )
        assert transaction_type_constraint, "Transaction type check constraint not found"
        
        # Check for status constraint
        status_constraint = any(
            "status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED')" in clause
            for clause in constraint_clauses
        )
        assert status_constraint, "Status check constraint not found"
        
        # Check for tier amount constraints
        tier_constraint = any(
            "tier_1 >= 0" in clause and "tier_2 >= 0" in clause and "tier_3 >= 0" in clause
            for clause in constraint_clauses
        )
        assert tier_constraint, "Tier amount check constraints not found"
    
    def test_indexes_exist(self, test_db):
        """Test that all required indexes exist."""
        query = """
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = 'investment_withdrawal_queue'
        """
        indexes = test_db.execute_query(query)
        
        index_names = [idx['indexname'] for idx in indexes]
        
        expected_indexes = [
            'idx_queue_uuid',
            'idx_queue_accountid',
            'idx_queue_status',
            'idx_queue_created_at',
            'idx_queue_transaction_type',
            'idx_queue_status_type'
        ]
        
        for expected_idx in expected_indexes:
            assert any(expected_idx in name for name in index_names), f"Index {expected_idx} not found"
    
    def test_views_exist(self, test_db):
        """Test that required views exist."""
        query = """
        SELECT table_name
        FROM information_schema.views
        WHERE table_schema = 'public'
        AND table_name IN ('queue_statistics', 'account_queue_summary')
        """
        views = test_db.execute_query(query)
        
        view_names = [view['table_name'] for view in views]
        assert 'queue_statistics' in view_names
        assert 'account_queue_summary' in view_names
    
    def test_triggers_exist(self, test_db):
        """Test that required triggers exist."""
        query = """
        SELECT trigger_name, event_manipulation
        FROM information_schema.triggers
        WHERE event_object_table = 'investment_withdrawal_queue'
        """
        triggers = test_db.execute_query(query)
        
        trigger_names = [trigger['trigger_name'] for trigger in triggers]
        
        expected_triggers = [
            'update_investment_withdrawal_queue_updated_at',
            'set_investment_withdrawal_queue_processed_at'
        ]
        
        for expected_trigger in expected_triggers:
            assert expected_trigger in trigger_names, f"Trigger {expected_trigger} not found"


class TestConstraintValidation:
    """Test database constraint validation."""
    
    def test_positive_tier_amounts_constraint(self, test_db):
        """Test that tier amounts must be non-negative."""
        invalid_request = TestDataGenerator.generate_investment_request(
            tier_1=Decimal('-100.00')
        )
        
        with pytest.raises(psycopg2.IntegrityError):
            test_db.create_test_queue_entry(**invalid_request)
    
    def test_transaction_type_constraint(self, test_db):
        """Test that transaction_type must be INVEST or WITHDRAW."""
        invalid_request = TestDataGenerator.generate_investment_request(
            transaction_type='INVALID'
        )
        
        with pytest.raises(psycopg2.IntegrityError):
            test_db.create_test_queue_entry(**invalid_request)
    
    def test_status_constraint(self, test_db):
        """Test that status must be one of the allowed values."""
        invalid_request = TestDataGenerator.generate_investment_request(
            status='INVALID_STATUS'
        )
        
        with pytest.raises(psycopg2.IntegrityError):
            test_db.create_test_queue_entry(**invalid_request)
    
    def test_not_null_constraints(self, test_db):
        """Test that required fields cannot be NULL."""
        # Test accountid NOT NULL
        invalid_request = TestDataGenerator.generate_investment_request()
        invalid_request['accountid'] = None
        
        with pytest.raises(psycopg2.IntegrityError):
            test_db.create_test_queue_entry(**invalid_request)
    
    def test_uuid_uniqueness_constraint(self, test_db):
        """Test that UUID must be unique."""
        # Create first entry
        request1 = TestDataGenerator.generate_investment_request()
        test_db.create_test_queue_entry(**request1)
        
        # Try to create second entry with same UUID
        request2 = TestDataGenerator.generate_investment_request()
        request2['uuid'] = request1['uuid']
        
        with pytest.raises(psycopg2.IntegrityError):
            test_db.create_test_queue_entry(**request2)
