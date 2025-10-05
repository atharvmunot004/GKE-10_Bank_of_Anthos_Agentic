# User-Portfolio-DB End-to-End Test Suite

Single-file comprehensive testing solution for the user-portfolio-db microservice.

## Quick Start

```bash
python test_user_portfolio_db_e2e.py
```

## What It Does

This single Python file handles everything:

1. **🐳 Container Management**: Builds and manages Docker containers
2. **🗄️ Database Setup**: Creates PostgreSQL database with schema
3. **📊 Test Data**: Inserts sample portfolio and transaction data
4. **🧪 Comprehensive Testing**: Runs 30+ test cases
5. **🧹 Automatic Cleanup**: Removes containers and images

## Files

- **`test_user_portfolio_db_e2e.py`** - Complete end-to-end test suite
- **`Dockerfile`** - PostgreSQL container for testing
- **`initdb/0-user-portfolio-schema.sql`** - Database schema
- **`README.md`** - This file

## Prerequisites

- **Python 3.7+**
- **Docker Desktop** (running)
- **Internet connection** (for PostgreSQL image)

## Test Coverage

- ✅ **Schema validation** (table structure, constraints, indexes)
- ✅ **Data integrity** (constraint enforcement, data types)
- ✅ **Query functionality** (CRUD operations, complex queries)
- ✅ **Performance testing** (query speed, index usage)
- ✅ **Error handling** (connection errors, constraint violations)
- ✅ **Integration testing** (complete lifecycle, transactions)

## Features

- **Automatic dependency installation** (psycopg2-binary)
- **Docker container lifecycle management**
- **Colored output with status indicators**
- **Comprehensive error handling**
- **Signal handling for graceful cleanup**
- **30+ individual test cases**

## Example Output

```
======================================================================
 User-Portfolio-DB End-to-End Test Suite
======================================================================
✓ Docker is available
✓ Docker image built successfully
✓ Container started: abc123def456
✓ Database is ready!
✓ Inserted 3 test portfolios and 4 test transactions

test_tier_allocation_constraint_invalid (__main__.UserPortfolioDBTestSuite) ... ok
test_tier_allocation_constraint_valid (__main__.UserPortfolioDBTestSuite) ... ok
test_get_user_portfolio (__main__.UserPortfolioDBTestSuite) ... ok
...

======================================================================
 Test Results Summary
======================================================================
ℹ Tests run: 30
✓ Passed: 30
ℹ Success Rate: 100.0%
✓ 🎉 All tests passed!
✓ Container stopped
✓ Container removed
✓ Image removed
```

## Database Schema

The test suite validates the following database structure:

### Tables
- **user_portfolios** - User portfolio information with tier-based allocation
- **portfolio_transactions** - Investment and withdrawal transaction records
- **portfolio_analytics** - Calculated portfolio metrics and analytics

### Key Features
- **Three-tier fund allocation** (TIER1, TIER2, TIER3)
- **Transaction tracking** for investments and withdrawals
- **Portfolio analytics** for performance metrics
- **Automatic timestamp updates** via triggers
- **Data consistency** constraints and foreign keys

## Troubleshooting

### Docker Not Running
```
✗ Docker command not found
```
**Solution**: Start Docker Desktop

### Port Already in Use
```
✗ Failed to start container: port is already allocated
```
**Solution**: The script automatically cleans up existing containers

### Python Dependencies
```
ModuleNotFoundError: No module named 'psycopg2'
```
**Solution**: Dependencies are installed automatically

## Manual Testing

If you need to inspect the database manually:

1. Comment out the cleanup section in the script
2. Run the script
3. Connect to the database:
   ```bash
   docker exec -it user-portfolio-db-test-e2e psql -U portfolio-admin -d user-portfolio-db
   ```
4. Clean up manually:
   ```bash
   docker stop user-portfolio-db-test-e2e
   docker rm user-portfolio-db-test-e2e
   docker rmi user-portfolio-db-test
   ```

## Test Categories

### Schema Validation Tests
- Table existence verification
- Column structure validation
- Constraint enforcement
- Index presence

### Constraint Tests
- Tier allocation constraints
- Transaction type validation
- Status constraint enforcement
- Foreign key relationships

### Query Functionality Tests
- Portfolio retrieval
- Transaction history
- Analytics calculations
- View functionality

### Performance Tests
- Index performance
- Query speed validation
- Large dataset handling

### Integration Tests
- Complete lifecycle testing
- Transaction rollback
- Cascade delete functionality
- Data consistency

## Related Services

The user-portfolio-db integrates with:
- **portfolio-reader-svc** - Read-only access to portfolio data
- **invest-svc** - Investment processing and portfolio updates
- **investment-manager-svc** - Orchestrates investment operations
- **consistency-manager-svc** - Maintains data consistency