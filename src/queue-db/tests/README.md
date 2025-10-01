# Queue-DB Testing Documentation

This directory contains comprehensive testing for the queue-db microservice, including unit tests, integration tests, and performance tests.

## Test Structure

```
tests/
├── unit/                          # Unit tests
│   ├── test_schema_validation.py  # Database schema tests
│   ├── test_business_logic.py     # Business logic tests
│   └── test_error_handling.py     # Error handling tests
├── integration/                   # Integration tests
│   └── test_end_to_end.py         # End-to-end workflow tests
├── load/                          # Load testing
│   └── locustfile.py              # Locust load tests
├── utils/                         # Test utilities
│   └── test_database.py           # Database test utilities
├── conftest.py                    # Pytest configuration
├── requirements.txt               # Test dependencies
└── README.md                      # This file
```

## Test Categories

### Unit Tests
- **Schema Validation**: Tests database table structure, constraints, indexes, and triggers
- **Business Logic**: Tests queue operations, status transitions, and validation rules
- **Error Handling**: Tests database errors, constraint violations, and error recovery

### Integration Tests
- **End-to-End Workflows**: Tests complete request processing workflows
- **Data Consistency**: Tests transaction rollback and concurrent operations
- **Performance Under Load**: Tests bulk operations and concurrent access

### Load Tests
- **Database Performance**: Tests database performance under various load conditions
- **Concurrent Access**: Tests concurrent read/write operations
- **Resource Management**: Tests connection pooling and resource cleanup

## Running Tests

### Prerequisites

1. **Install Dependencies**:
   ```bash
   pip install -r tests/requirements.txt
   ```

2. **Set up Test Database**:
   ```bash
   # Start PostgreSQL container
   docker run -d --name queue-db-test \
     -e POSTGRES_DB=queue-db-test \
     -e POSTGRES_USER=queue-admin \
     -e POSTGRES_PASSWORD=queue-pwd \
     -p 5432:5432 \
     postgres:15-alpine
   ```

3. **Set Environment Variables**:
   ```bash
   export TEST_QUEUE_DB_URI="postgresql://queue-admin:queue-pwd@localhost:5432/queue-db-test"
   ```

### Running All Tests

```bash
# Run all tests
./run_tests.sh

# Run with coverage
./run_tests.sh -c

# Run in parallel
./run_tests.sh -p
```

### Running Specific Test Types

```bash
# Unit tests only
./run_tests.sh -t unit

# Integration tests only
./run_tests.sh -t integration

# Performance tests only
./run_tests.sh -t performance
```

### Running Individual Test Files

```bash
# Run specific test file
pytest tests/unit/test_schema_validation.py -v

# Run specific test class
pytest tests/unit/test_business_logic.py::TestQueueOperations -v

# Run specific test method
pytest tests/unit/test_business_logic.py::TestQueueOperations::test_create_investment_request -v
```

### Running with Different Options

```bash
# Verbose output
pytest tests/ -v

# Stop on first failure
pytest tests/ -x

# Run only failed tests from last run
pytest tests/ --lf

# Run tests matching pattern
pytest tests/ -k "test_create"

# Run tests with specific marker
pytest tests/ -m "unit"
```

## Load Testing

### Using Locust

1. **Start the queue-db service**:
   ```bash
   kubectl port-forward service/queue-db 5432:5432
   ```

2. **Run load tests**:
   ```bash
   # Basic load test
   locust -f tests/load/locustfile.py --host=localhost:5432

   # Custom load test
   locust -f tests/load/locustfile.py \
     --host=localhost:5432 \
     --users=50 \
     --spawn-rate=5 \
     --run-time=60s
   ```

3. **Access Locust Web UI**:
   Open http://localhost:8089 in your browser

### Load Test Scenarios

- **Write Heavy**: 70% writes, 30% reads
- **Read Heavy**: 30% writes, 70% reads
- **Balanced**: 50% writes, 50% reads
- **Burst Load**: Sudden spikes in traffic
- **Sustained Load**: Constant load over time

## Test Data

### Sample Data Generation

The test utilities provide functions to generate realistic test data:

```python
from tests.utils.test_database import TestDataGenerator

# Generate investment request
request = TestDataGenerator.generate_investment_request(
    accountid='1011226111',
    tier_1=Decimal('1000.50'),
    tier_2=Decimal('2000.75'),
    tier_3=Decimal('500.25')
)

# Generate withdrawal request
request = TestDataGenerator.generate_withdrawal_request(
    accountid='1011226111',
    tier_1=Decimal('500.00'),
    tier_2=Decimal('1000.00'),
    tier_3=Decimal('250.00')
)
```

### Test Data Cleanup

Tests automatically clean up data after execution. For manual cleanup:

```python
# Clear all test data
test_db.clear_test_data()

# Clear specific account data
test_db.execute_update(
    "DELETE FROM investment_withdrawal_queue WHERE accountid = %s",
    ('1011226111',)
)
```

## Test Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TEST_QUEUE_DB_URI` | Test database connection string | `postgresql://queue-admin:queue-pwd@localhost:5432/queue-db-test` |
| `POSTGRES_DB` | Test database name | `queue-db-test` |
| `POSTGRES_USER` | Test database user | `queue-admin` |
| `POSTGRES_PASSWORD` | Test database password | `queue-pwd` |

### Pytest Configuration

The `pytest.ini` file contains test configuration:

- Test discovery patterns
- Markers for different test types
- Coverage configuration
- Output formatting

### Test Markers

- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.performance`: Performance tests
- `@pytest.mark.slow`: Slow running tests
- `@pytest.mark.database`: Database tests

## Test Reports

### HTML Report

After running tests, view the HTML report:

```bash
open test-reports/report.html
```

### Coverage Report

View coverage report:

```bash
open test-reports/coverage/index.html
```

### JUnit XML

For CI/CD integration, JUnit XML reports are generated:

```bash
# View JUnit XML
cat test-reports/junit.xml
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Queue-DB Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_DB: queue-db-test
          POSTGRES_USER: queue-admin
          POSTGRES_PASSWORD: queue-pwd
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    
    - name: Install dependencies
      run: |
        pip install -r tests/requirements.txt
    
    - name: Run tests
      run: |
        ./run_tests.sh -c
      env:
        TEST_QUEUE_DB_URI: postgresql://queue-admin:queue-pwd@localhost:5432/queue-db-test
    
    - name: Upload coverage reports
      uses: codecov/codecov-action@v1
      with:
        file: test-reports/coverage.xml
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**:
   - Check if PostgreSQL is running
   - Verify connection string
   - Check network connectivity

2. **Test Data Conflicts**:
   - Ensure test data cleanup is working
   - Check for concurrent test execution
   - Verify database isolation

3. **Performance Test Failures**:
   - Check system resources
   - Verify database configuration
   - Monitor connection pool settings

### Debug Commands

```bash
# Run tests with debug output
pytest tests/ -v -s --tb=long

# Run single test with debug
pytest tests/unit/test_business_logic.py::TestQueueOperations::test_create_investment_request -v -s

# Check test database connection
python -c "
from tests.utils.test_database import TestDatabase
db = TestDatabase()
db.connect()
print('Connection successful')
db.disconnect()
"
```

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Data Cleanup**: Always clean up test data
3. **Realistic Data**: Use realistic test data
4. **Error Testing**: Test both success and failure scenarios
5. **Performance Monitoring**: Monitor test execution time
6. **Documentation**: Keep test documentation up to date

## Contributing

When adding new tests:

1. Follow the existing test structure
2. Use appropriate test markers
3. Include docstrings for test methods
4. Add test data cleanup
5. Update this documentation if needed
