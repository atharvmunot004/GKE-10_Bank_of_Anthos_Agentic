# User Request Queue Service

A microservice for processing queue transactions in batches and forwarding them to the bank-asset-agent service.

## Overview

This microservice polls the queue-db for batches of 10 transactions, calculates tier differences between INVEST and WITHDRAW operations, and forwards the aggregated data to the bank-asset-agent service.

## Architecture

### Core Components

- **Queue Poller**: Continuously polls queue-db for pending transactions
- **Tier Calculator**: Calculates net differences between INVEST and WITHDRAW amounts
- **Asset Agent Client**: Communicates with bank-asset-agent service
- **Status Manager**: Updates transaction statuses in the database

### Technology Stack

- **Language**: Python 3.9+
- **Framework**: FastAPI
- **Database Client**: asyncpg (PostgreSQL async driver)
- **HTTP Client**: httpx (async HTTP client)
- **Logging**: structlog
- **Monitoring**: prometheus-client
- **Configuration**: pydantic-settings

## Workflow

1. **Poll Queue**: Check queue-db for pending transactions (minimum 10 required)
2. **Fetch Batch**: Retrieve batch of 10 transactions ordered by creation time
3. **Calculate Tiers**: Compute net differences for each tier (T1, T2, T3)
4. **Forward Request**: Send aggregated data to bank-asset-agent
5. **Update Status**: Mark transactions as COMPLETED or FAILED based on response

### Tier Calculation Logic

```
T1 = sum(tier1, 'INVEST') - sum(tier1, 'WITHDRAW')
T2 = sum(tier2, 'INVEST') - sum(tier2, 'WITHDRAW')  
T3 = sum(tier3, 'INVEST') - sum(tier3, 'WITHDRAW')
```

## API Endpoints

- `GET /health` - Health check endpoint
- `GET /ready` - Readiness check endpoint
- `GET /metrics` - Prometheus metrics
- `POST /api/v1/poll` - Manually trigger queue polling
- `GET /api/v1/batch/{batch_id}/status` - Get batch processing status
- `GET /api/v1/queue/stats` - Get queue statistics

## Configuration

### Environment Variables

- `QUEUE_DB_URI` - PostgreSQL connection string
- `BANK_ASSET_AGENT_URL` - Bank asset agent service URL
- `POLLING_INTERVAL` - Queue polling interval in seconds (default: 5)
- `BATCH_SIZE` - Number of transactions per batch (default: 10)
- `LOG_LEVEL` - Logging level (default: INFO)
- `SERVICE_PORT` - Service port (default: 8080)

## Testing

### Test Structure

```
tests/
├── conftest.py                    # Test fixtures and configuration
├── test_models.py                 # ✅ Pydantic model validation tests
├── test_tier_calculator.py        # ✅ Business logic calculation tests
├── test_utils.py                  # ✅ Utility function tests
├── test_services.py               # Service layer tests
├── test_database.py               # Database layer tests
├── test_api.py                    # FastAPI endpoint tests
├── integration/
│   ├── test_database_integration.py        # Database integration tests
│   └── test_external_service_integration.py # External service tests
└── e2e/
    └── test_end_to_end_workflow.py         # Complete workflow tests
```

### Running Tests

```bash
# Run core unit tests (39 tests passing)
python -m pytest tests/test_models.py tests/test_tier_calculator.py tests/test_utils.py -v

# Run with coverage
python -m pytest tests/test_models.py tests/test_tier_calculator.py tests/test_utils.py -v --cov=. --cov-report=html

# Run all tests using the test script
./run_tests.sh
```

### Test Coverage

- **Models**: 100% coverage
- **Utils**: 100% coverage  
- **Config**: 100% coverage
- **Tier Calculator**: 100% coverage
- **Services**: Partial coverage (requires mock improvements)
- **Database**: Requires integration testing
- **API**: Requires FastAPI test client improvements

## Deployment

### Docker

```bash
# Build image
docker build -t user-request-queue-svc:v1.0.0 .

# Run container
docker run -p 8080:8080 \
  -e QUEUE_DB_URI="postgresql://queue-admin:queue-pwd@queue-db:5432/queue-db" \
  -e BANK_ASSET_AGENT_URL="http://bank-asset-agent:8080/api/v1/process-portfolio" \
  user-request-queue-svc:v1.0.0
```

### Kubernetes

```bash
# Deploy to Kubernetes
kubectl apply -f ../kubernetes-manifests/user-request-queue-svc.yaml

# Check deployment status
kubectl get pods -l app=user-request-queue-svc
kubectl get services -l app=user-request-queue-svc
```

## Monitoring

### Metrics

- `batches_processed_total` - Counter of processed batches
- `transactions_processed_total` - Counter of processed transactions
- `batch_processing_duration_seconds` - Histogram of batch processing time
- `queue_size` - Gauge of current queue size
- `failed_batches_total` - Counter of failed batches
- `external_service_response_time_seconds` - Histogram of asset agent response time

### Health Checks

- **Liveness**: `/health` - Database connectivity and external service availability
- **Readiness**: `/ready` - Service initialization complete
- **Startup**: Service startup validation

## Error Handling

### Database Errors
- Connection failures: Retry with exponential backoff
- Query timeouts: Log error and continue polling
- Transaction rollbacks: Mark batch as failed

### External Service Errors
- Timeouts: Retry with backoff (3 attempts)
- Service unavailable: Mark batch as failed, retry later
- Invalid responses: Log error and mark as failed

### Data Validation Errors
- Invalid tier values: Skip invalid transactions
- Missing required fields: Log and skip transaction

## Development

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt
```

### Running Locally

```bash
# Start the service
python main.py

# Or with uvicorn
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

### Code Quality

- **Linting**: Use flake8, black for code formatting
- **Type Checking**: Use mypy for static type checking
- **Testing**: Comprehensive test suite with pytest
- **Coverage**: Maintain >80% test coverage

## Files Structure

```
user-request-queue-svc/
├── main.py                    # FastAPI application entry point
├── config.py                  # Configuration management
├── models.py                  # Pydantic data models
├── database.py                # Database connection and queries
├── services.py                # Core business logic
├── utils.py                   # Utility functions and metrics
├── requirements.txt           # Production dependencies
├── requirements-test.txt      # Test dependencies
├── pytest.ini                # Pytest configuration
├── Dockerfile                 # Container definition
├── run_tests.sh              # Test execution script
├── README.md                 # This file
└── tests/                    # Test suite
```

## Contributing

1. Follow the existing code structure and patterns
2. Add comprehensive tests for new features
3. Update documentation for API changes
4. Ensure all tests pass before submitting changes
5. Follow semantic versioning for releases

## License

Copyright 2024 - Bank of Anthos Project
