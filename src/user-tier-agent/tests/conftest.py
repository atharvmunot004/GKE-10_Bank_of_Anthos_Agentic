"""
Pytest configuration and fixtures
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
import httpx
from langchain_google_genai import ChatGoogleGenerativeAI

from main import app
from app.core.config import settings
from app.models.schemas import TierAllocationRequest, PurposeEnum


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_client():
    """Create test client for FastAPI app"""
    return TestClient(app)


@pytest.fixture
def mock_llm():
    """Mock Gemini LLM"""
    mock = Mock(spec=ChatGoogleGenerativeAI)
    mock.invoke = AsyncMock()
    return mock


@pytest.fixture
def sample_allocation_request():
    """Sample tier allocation request"""
    return TierAllocationRequest(
        uuid="123e4567-e89b-12d3-a456-426614174000",
        accountid="test-account-123",
        amount=10000.0,
        purpose=PurposeEnum.INVEST
    )


@pytest.fixture
def sample_transaction_data():
    """Sample transaction data"""
    return {
        "transactions": [
            {
                "TRANSACTION_ID": "tx-001",
                "FROM_ACCT": "test-account-123",
                "TO_ACCT": "merchant-001",
                "FROM_ROUTE": "123456789",
                "TO_ROUTE": "987654321",
                "AMOUNT": 50.0,
                "TIMESTAMP": "2024-01-01T10:00:00Z"
            },
            {
                "TRANSACTION_ID": "tx-002",
                "FROM_ACCT": "employer-001",
                "TO_ACCT": "test-account-123",
                "FROM_ROUTE": "111111111",
                "TO_ROUTE": "123456789",
                "AMOUNT": 5000.0,
                "TIMESTAMP": "2024-01-01T09:00:00Z"
            }
        ],
        "count": 2,
        "accountid": "test-account-123"
    }


@pytest.fixture
def mock_http_client():
    """Mock HTTP client for external service calls"""
    mock = Mock(spec=httpx.AsyncClient)
    mock.get = AsyncMock()
    mock.post = AsyncMock()
    return mock


@pytest.fixture
def mock_agent_response():
    """Mock agent response"""
    return {
        "output": "Based on the transaction history analysis, I recommend the following allocation:\nTier1: 1000.0\nTier2: 2000.0\nTier3: 7000.0\n\nReasoning: The user shows regular income patterns and moderate spending, suitable for this distribution."
    }


@pytest.fixture
def mock_health_response():
    """Mock health check response"""
    return {
        "status": "healthy",
        "dependencies": [
            {
                "name": "ledger-db",
                "status": "healthy",
                "url": "http://ledger-db:8080",
                "response_time": 0.1
            }
        ],
        "timestamp": 1640995200.0
    }


@pytest.fixture(autouse=True)
def mock_environment_variables(monkeypatch):
    """Mock environment variables for testing"""
    monkeypatch.setenv("GEMINI_API_KEY", "test-api-key")
    monkeypatch.setenv("LEDGER_DB_URL", "http://test-ledger-db:8080")
    monkeypatch.setenv("QUEUE_DB_URL", "http://test-queue-db:8080")
    monkeypatch.setenv("PORTFOLIO_DB_URL", "http://test-portfolio-db:8080")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
