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
Test utilities for queue-db microservice testing.
Provides database connection, test data setup, and common test functions.
"""

import os
import psycopg2
import psycopg2.extras
import pytest
import uuid
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timezone


class TestDatabase:
    """Test database utility class for managing test database connections and operations."""
    
    def __init__(self, connection_string: str = None):
        """Initialize test database connection."""
        self.connection_string = connection_string or self._get_test_connection_string()
        self.connection = None
        self.cursor = None
    
    def _get_test_connection_string(self) -> str:
        """Get test database connection string from environment or use default."""
        return os.getenv(
            'TEST_QUEUE_DB_URI',
            'postgresql://queue-admin:queue-pwd@localhost:5432/queue-db-test'
        )
    
    def connect(self):
        """Establish database connection."""
        try:
            self.connection = psycopg2.connect(self.connection_string)
            self.connection.autocommit = False
            self.cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        except psycopg2.Error as e:
            raise ConnectionError(f"Failed to connect to test database: {e}")
    
    def disconnect(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if exc_type:
            self.connection.rollback()
        else:
            self.connection.commit()
        self.disconnect()
    
    def execute_query(self, query: str, params: Tuple = None) -> List[Dict]:
        """Execute a SELECT query and return results as list of dictionaries."""
        self.cursor.execute(query, params)
        return [dict(row) for row in self.cursor.fetchall()]
    
    def execute_update(self, query: str, params: Tuple = None) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return number of affected rows."""
        self.cursor.execute(query, params)
        return self.cursor.rowcount
    
    def create_test_queue_entry(self, **kwargs) -> Dict:
        """Create a test queue entry with default values."""
        defaults = {
            'accountid': '1011226111',
            'tier_1': Decimal('1000.50'),
            'tier_2': Decimal('2000.75'),
            'tier_3': Decimal('500.25'),
            'uuid': str(uuid.uuid4()),
            'transaction_type': 'INVEST',
            'status': 'PENDING'
        }
        defaults.update(kwargs)
        
        query = """
        INSERT INTO investment_withdrawal_queue 
        (accountid, tier_1, tier_2, tier_3, uuid, transaction_type, status)
        VALUES (%(accountid)s, %(tier_1)s, %(tier_2)s, %(tier_3)s, %(uuid)s, %(transaction_type)s, %(status)s)
        RETURNING *
        """
        
        self.cursor.execute(query, defaults)
        result = self.cursor.fetchone()
        return dict(result)
    
    def get_queue_entry(self, uuid: str) -> Optional[Dict]:
        """Get a queue entry by UUID."""
        query = "SELECT * FROM investment_withdrawal_queue WHERE uuid = %s"
        results = self.execute_query(query, (uuid,))
        return results[0] if results else None
    
    def get_queue_entries_by_account(self, accountid: str) -> List[Dict]:
        """Get all queue entries for an account."""
        query = "SELECT * FROM investment_withdrawal_queue WHERE accountid = %s ORDER BY created_at DESC"
        return self.execute_query(query, (accountid,))
    
    def update_queue_status(self, uuid: str, status: str) -> bool:
        """Update queue entry status."""
        query = "UPDATE investment_withdrawal_queue SET status = %s WHERE uuid = %s"
        rows_affected = self.execute_update(query, (status, uuid))
        return rows_affected > 0
    
    def get_queue_statistics(self) -> Dict:
        """Get queue statistics."""
        query = """
        SELECT 
            status,
            transaction_type,
            COUNT(*) as count,
            AVG(EXTRACT(EPOCH FROM (COALESCE(processed_at, CURRENT_TIMESTAMP) - created_at))) as avg_processing_time_seconds
        FROM investment_withdrawal_queue
        GROUP BY status, transaction_type
        """
        results = self.execute_query(query)
        return {f"{row['status']}_{row['transaction_type']}": dict(row) for row in results}
    
    def clear_test_data(self):
        """Clear all test data from the queue table."""
        self.execute_update("DELETE FROM investment_withdrawal_queue")
    
    def setup_test_schema(self):
        """Set up test database schema."""
        schema_file = os.path.join(os.path.dirname(__file__), '../../initdb/0-queue-schema.sql')
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        # Split by semicolon and execute each statement
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        for statement in statements:
            if statement:
                self.cursor.execute(statement)


@pytest.fixture
def test_db():
    """Pytest fixture for test database."""
    db = TestDatabase()
    with db:
        db.setup_test_schema()
        yield db
        db.clear_test_data()


@pytest.fixture
def sample_investment_request():
    """Sample investment request data for testing."""
    return {
        'accountid': '1011226111',
        'tier_1': Decimal('1000.50'),
        'tier_2': Decimal('2000.75'),
        'tier_3': Decimal('500.25'),
        'uuid': str(uuid.uuid4()),
        'transaction_type': 'INVEST',
        'status': 'PENDING'
    }


@pytest.fixture
def sample_withdrawal_request():
    """Sample withdrawal request data for testing."""
    return {
        'accountid': '1011226111',
        'tier_1': Decimal('500.00'),
        'tier_2': Decimal('1000.00'),
        'tier_3': Decimal('250.00'),
        'uuid': str(uuid.uuid4()),
        'transaction_type': 'WITHDRAW',
        'status': 'PENDING'
    }


class TestDataGenerator:
    """Utility class for generating test data."""
    
    @staticmethod
    def generate_investment_request(accountid: str = None, **kwargs) -> Dict:
        """Generate a valid investment request."""
        defaults = {
            'accountid': accountid or '1011226111',
            'tier_1': Decimal('1000.50'),
            'tier_2': Decimal('2000.75'),
            'tier_3': Decimal('500.25'),
            'uuid': str(uuid.uuid4()),
            'transaction_type': 'INVEST',
            'status': 'PENDING'
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def generate_withdrawal_request(accountid: str = None, **kwargs) -> Dict:
        """Generate a valid withdrawal request."""
        defaults = {
            'accountid': accountid or '1011226111',
            'tier_1': Decimal('500.00'),
            'tier_2': Decimal('1000.00'),
            'tier_3': Decimal('250.00'),
            'uuid': str(uuid.uuid4()),
            'transaction_type': 'WITHDRAW',
            'status': 'PENDING'
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def generate_invalid_requests() -> List[Dict]:
        """Generate various invalid request data for negative testing."""
        return [
            # Negative tier amounts
            {
                'accountid': '1011226111',
                'tier_1': Decimal('-100.00'),
                'tier_2': Decimal('2000.75'),
                'tier_3': Decimal('500.25'),
                'uuid': str(uuid.uuid4()),
                'transaction_type': 'INVEST',
                'status': 'PENDING'
            },
            # Invalid transaction type
            {
                'accountid': '1011226111',
                'tier_1': Decimal('1000.50'),
                'tier_2': Decimal('2000.75'),
                'tier_3': Decimal('500.25'),
                'uuid': str(uuid.uuid4()),
                'transaction_type': 'INVALID',
                'status': 'PENDING'
            },
            # Invalid status
            {
                'accountid': '1011226111',
                'tier_1': Decimal('1000.50'),
                'tier_2': Decimal('2000.75'),
                'tier_3': Decimal('500.25'),
                'uuid': str(uuid.uuid4()),
                'transaction_type': 'INVEST',
                'status': 'INVALID_STATUS'
            },
            # Missing required fields (will be caught by NOT NULL constraints)
            {
                'accountid': None,
                'tier_1': Decimal('1000.50'),
                'tier_2': Decimal('2000.75'),
                'tier_3': Decimal('500.25'),
                'uuid': str(uuid.uuid4()),
                'transaction_type': 'INVEST',
                'status': 'PENDING'
            }
        ]


def assert_queue_entry_valid(entry: Dict):
    """Assert that a queue entry has valid structure and data."""
    required_fields = [
        'queue_id', 'accountid', 'tier_1', 'tier_2', 'tier_3',
        'uuid', 'transaction_type', 'status', 'created_at', 'updated_at'
    ]
    
    for field in required_fields:
        assert field in entry, f"Missing required field: {field}"
    
    # Validate data types and constraints
    assert isinstance(entry['tier_1'], Decimal)
    assert isinstance(entry['tier_2'], Decimal)
    assert isinstance(entry['tier_3'], Decimal)
    assert entry['tier_1'] >= 0
    assert entry['tier_2'] >= 0
    assert entry['tier_3'] >= 0
    assert entry['transaction_type'] in ['INVEST', 'WITHDRAW']
    assert entry['status'] in ['PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED']
    assert len(entry['uuid']) == 36  # UUID4 format
    assert len(entry['accountid']) <= 20
