"""
Pytest configuration and fixtures for user-request-queue-svc tests
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal
from datetime import datetime
from typing import List

from models import QueueTransaction, TransactionType, TransactionStatus
from database import DatabaseManager
from services import QueueProcessor, AssetAgentClient


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_transactions() -> List[QueueTransaction]:
    """Fixture providing sample transactions for testing"""
    return [
        QueueTransaction(
            uuid="uuid-1",
            accountid="12345678901234567890",
            tier1=Decimal("1000.00"),
            tier2=Decimal("2000.00"),
            tier3=Decimal("500.00"),
            purpose=TransactionType.INVEST,
            status=TransactionStatus.PENDING,
            created_at=datetime.utcnow()
        ),
        QueueTransaction(
            uuid="uuid-2",
            accountid="12345678901234567890",
            tier1=Decimal("500.00"),
            tier2=Decimal("1000.00"),
            tier3=Decimal("250.00"),
            purpose=TransactionType.WITHDRAW,
            status=TransactionStatus.PENDING,
            created_at=datetime.utcnow()
        ),
        QueueTransaction(
            uuid="uuid-3",
            accountid="98765432109876543210",
            tier1=Decimal("750.00"),
            tier2=Decimal("1500.00"),
            tier3=Decimal("375.00"),
            purpose=TransactionType.INVEST,
            status=TransactionStatus.PENDING,
            created_at=datetime.utcnow()
        )
    ]


@pytest.fixture
def sample_invest_transactions() -> List[QueueTransaction]:
    """Fixture providing only INVEST transactions"""
    return [
        QueueTransaction(
            uuid="invest-1",
            accountid="12345678901234567890",
            tier1=Decimal("1000.00"),
            tier2=Decimal("2000.00"),
            tier3=Decimal("500.00"),
            purpose=TransactionType.INVEST,
            status=TransactionStatus.PENDING
        ),
        QueueTransaction(
            uuid="invest-2",
            accountid="12345678901234567890",
            tier1=Decimal("500.00"),
            tier2=Decimal("1000.00"),
            tier3=Decimal("250.00"),
            purpose=TransactionType.INVEST,
            status=TransactionStatus.PENDING
        )
    ]


@pytest.fixture
def sample_withdraw_transactions() -> List[QueueTransaction]:
    """Fixture providing only WITHDRAW transactions"""
    return [
        QueueTransaction(
            uuid="withdraw-1",
            accountid="12345678901234567890",
            tier1=Decimal("300.00"),
            tier2=Decimal("600.00"),
            tier3=Decimal("150.00"),
            purpose=TransactionType.WITHDRAW,
            status=TransactionStatus.PENDING
        ),
        QueueTransaction(
            uuid="withdraw-2",
            accountid="12345678901234567890",
            tier1=Decimal("200.00"),
            tier2=Decimal("400.00"),
            tier3=Decimal("100.00"),
            purpose=TransactionType.WITHDRAW,
            status=TransactionStatus.PENDING
        )
    ]


@pytest.fixture
def sample_database_rows():
    """Fixture providing sample database row data"""
    return [
        {
            'uuid': 'db-uuid-1',
            'accountid': '12345678901234567890',
            'tier_1': Decimal('1000.00'),
            'tier_2': Decimal('2000.00'),
            'tier_3': Decimal('500.00'),
            'transaction_type': 'INVEST',
            'status': 'PENDING',
            'created_at': datetime.utcnow(),
            'updated_at': None,
            'processed_at': None
        },
        {
            'uuid': 'db-uuid-2',
            'accountid': '12345678901234567890',
            'tier_1': Decimal('500.00'),
            'tier_2': Decimal('1000.00'),
            'tier_3': Decimal('250.00'),
            'transaction_type': 'WITHDRAW',
            'status': 'PENDING',
            'created_at': datetime.utcnow(),
            'updated_at': None,
            'processed_at': None
        }
    ]


@pytest.fixture
def mock_database_manager():
    """Fixture providing a mocked database manager"""
    mock_db = MagicMock(spec=DatabaseManager)
    mock_db.initialize = AsyncMock()
    mock_db.close = AsyncMock()
    mock_db.is_connected = AsyncMock(return_value=True)
    mock_db.count_pending_requests = AsyncMock(return_value=10)
    mock_db.fetch_batch = AsyncMock(return_value=[])
    mock_db.update_batch_status = AsyncMock(return_value=True)
    mock_db.get_transaction_by_uuid = AsyncMock(return_value=None)
    return mock_db


@pytest.fixture
def mock_asset_agent_client():
    """Fixture providing a mocked asset agent client"""
    mock_client = MagicMock(spec=AssetAgentClient)
    mock_client.is_available = AsyncMock(return_value=True)
    mock_client.process_portfolio = AsyncMock()
    return mock_client


@pytest.fixture
def mock_queue_processor(mock_asset_agent_client):
    """Fixture providing a mocked queue processor"""
    mock_processor = MagicMock(spec=QueueProcessor)
    mock_processor.asset_agent_client = mock_asset_agent_client
    mock_processor.is_processing = False
    mock_processor.process_batch = AsyncMock(return_value=True)
    mock_processor.poll_and_process = AsyncMock(return_value=1)
    mock_processor.start_polling = AsyncMock()
    return mock_processor


@pytest.fixture
def mock_asyncpg_pool():
    """Fixture providing a mocked asyncpg connection pool"""
    mock_pool = AsyncMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
    return mock_pool, mock_conn


@pytest.fixture
def mock_httpx_client():
    """Fixture providing a mocked httpx client"""
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "COMPLETED"}
    mock_response.raise_for_status = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.get = AsyncMock(return_value=mock_response)
    return mock_client, mock_response


@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset Prometheus metrics before each test"""
    # Import metrics and reset them
    from prometheus_client import REGISTRY
    
    # Clear metrics (this is a simplified approach)
    # In a real scenario, you might want to use a separate registry for tests
    yield
    
    # Cleanup after test if needed
    pass


@pytest.fixture
def test_config():
    """Fixture providing test configuration"""
    return {
        "service_port": 8080,
        "log_level": "DEBUG",
        "polling_interval": 1,  # Faster for tests
        "batch_size": 5,  # Smaller for tests
        "max_retries": 2,  # Fewer retries for tests
        "retry_delay": 0.1,  # Faster retries for tests
        "queue_db_host": "test-queue-db",
        "queue_db_port": 5432,
        "queue_db_name": "test-queue-db",
        "queue_db_user": "test-user",
        "queue_db_password": "test-password",
        "bank_asset_agent_url": "http://test-bank-asset-agent:8080/api/v1/process-portfolio",
        "bank_asset_agent_timeout": 5,  # Shorter timeout for tests
        "connection_pool_size": 2,  # Smaller pool for tests
        "max_overflow": 5
    }


@pytest.fixture
def edge_case_transactions():
    """Fixture providing edge case transactions for testing"""
    return [
        # Zero amounts
        QueueTransaction(
            uuid="zero-1",
            accountid="12345678901234567890",
            tier1=Decimal("0.00"),
            tier2=Decimal("0.00"),
            tier3=Decimal("0.00"),
            purpose=TransactionType.INVEST,
            status=TransactionStatus.PENDING
        ),
        # Very small amounts
        QueueTransaction(
            uuid="small-1",
            accountid="12345678901234567890",
            tier1=Decimal("0.00000001"),
            tier2=Decimal("0.00000001"),
            tier3=Decimal("0.00000001"),
            purpose=TransactionType.WITHDRAW,
            status=TransactionStatus.PENDING
        ),
        # Very large amounts
        QueueTransaction(
            uuid="large-1",
            accountid="12345678901234567890",
            tier1=Decimal("999999999.99999999"),
            tier2=Decimal("999999999.99999999"),
            tier3=Decimal("999999999.99999999"),
            purpose=TransactionType.INVEST,
            status=TransactionStatus.PENDING
        )
    ]


@pytest.fixture
def performance_test_transactions():
    """Fixture providing a large number of transactions for performance testing"""
    transactions = []
    for i in range(100):
        transactions.append(
            QueueTransaction(
                uuid=f"perf-uuid-{i}",
                accountid=f"account-{i % 10}",  # 10 different accounts
                tier1=Decimal(f"{(i * 10) % 10000}.{i % 100:02d}"),
                tier2=Decimal(f"{(i * 20) % 10000}.{i % 100:02d}"),
                tier3=Decimal(f"{(i * 5) % 10000}.{i % 100:02d}"),
                purpose=TransactionType.INVEST if i % 2 == 0 else TransactionType.WITHDRAW,
                status=TransactionStatus.PENDING,
                created_at=datetime.utcnow()
            )
        )
    return transactions


@pytest.fixture(scope="session")
def docker_compose_file():
    """Fixture providing docker-compose file path for integration tests"""
    return "tests/docker-compose.test.yml"


@pytest.fixture
def error_scenarios():
    """Fixture providing various error scenarios for testing"""
    return {
        "database_connection_error": Exception("Database connection failed"),
        "database_query_error": Exception("Query execution failed"),
        "external_service_timeout": Exception("Request timeout"),
        "external_service_error": Exception("External service unavailable"),
        "invalid_response_format": Exception("Invalid response format"),
        "network_error": Exception("Network unreachable")
    }
