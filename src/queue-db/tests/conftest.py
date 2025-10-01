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
Pytest configuration and fixtures for queue-db testing.
"""

import os
import pytest
import tempfile
import subprocess
import time
from testcontainers.postgres import PostgresContainer
from tests.utils.test_database import TestDatabase


@pytest.fixture(scope="session")
def postgres_container():
    """Start PostgreSQL container for testing."""
    with PostgresContainer("postgres:15-alpine") as postgres:
        # Set up the database
        postgres.get_connection_url()
        
        # Wait for container to be ready
        time.sleep(5)
        
        yield postgres


@pytest.fixture(scope="session")
def test_database_url(postgres_container):
    """Get test database connection URL."""
    return postgres_container.get_connection_url()


@pytest.fixture
def test_db(test_database_url):
    """Test database fixture with proper setup and teardown."""
    db = TestDatabase(test_database_url)
    
    with db:
        # Set up test schema
        db.setup_test_schema()
        
        yield db
        
        # Clean up test data
        db.clear_test_data()


@pytest.fixture(scope="session")
def test_data_dir():
    """Get test data directory."""
    return os.path.join(os.path.dirname(__file__), 'data')


@pytest.fixture
def sample_accounts():
    """Sample account IDs for testing."""
    return [
        '1011226111',
        '1011226112', 
        '1011226113',
        '1011226114',
        '1011226115'
    ]


@pytest.fixture
def sample_investment_data():
    """Sample investment data for testing."""
    return {
        'tier_1': 1000.50,
        'tier_2': 2000.75,
        'tier_3': 500.25
    }


@pytest.fixture
def sample_withdrawal_data():
    """Sample withdrawal data for testing."""
    return {
        'tier_1': 500.00,
        'tier_2': 1000.00,
        'tier_3': 250.00
    }


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    os.environ['TEST_QUEUE_DB_URI'] = 'postgresql://test:test@localhost:5432/test'
    os.environ['POSTGRES_DB'] = 'test'
    os.environ['POSTGRES_USER'] = 'test'
    os.environ['POSTGRES_PASSWORD'] = 'test'


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file location."""
    for item in items:
        # Add markers based on test file location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add slow marker for performance tests
        if "performance" in str(item.fspath) or "load" in str(item.fspath):
            item.add_marker(pytest.mark.slow)
            item.add_marker(pytest.mark.performance)


# Test data cleanup
@pytest.fixture(autouse=True)
def cleanup_test_data(test_db):
    """Automatically clean up test data after each test."""
    yield
    if hasattr(test_db, 'clear_test_data'):
        test_db.clear_test_data()


# Performance testing configuration
@pytest.fixture
def performance_config():
    """Configuration for performance tests."""
    return {
        'max_response_time': 1.0,  # seconds
        'max_memory_usage': 100,   # MB
        'concurrent_users': 10,
        'test_duration': 30        # seconds
    }


# Load testing configuration
@pytest.fixture
def load_test_config():
    """Configuration for load tests."""
    return {
        'users': 50,
        'spawn_rate': 5,
        'run_time': '60s',
        'host': 'http://localhost:5432'
    }
