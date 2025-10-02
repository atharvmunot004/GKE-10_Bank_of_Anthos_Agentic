# Assets-DB End-to-End Test Suite

Single-file comprehensive testing solution for the assets-db microservice.

## Quick Start

```bash
python test_assets_db_e2e.py
```

## What It Does

This single Python file handles everything:

1. **🐳 Container Management**: Builds and manages Docker containers
2. **🗄️ Database Setup**: Creates PostgreSQL database with schema
3. **📊 Test Data**: Inserts sample data for testing
4. **🧪 Comprehensive Testing**: Runs 30+ test cases
5. **🧹 Automatic Cleanup**: Removes containers and images

## Files

- **`test_assets_db_e2e.py`** - Complete end-to-end test suite
- **`Dockerfile`** - PostgreSQL container for testing
- **`initdb/0-assets-schema.sql`** - Database schema
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
 Assets-DB End-to-End Test Suite
======================================================================
✓ Docker is available
✓ Docker image built successfully
✓ Container started: abc123def456
✓ Database is ready!
✓ Inserted 6 test assets

test_amount_constraint_invalid_values (__main__.AssetsDBTestSuite) ... ok
test_amount_constraint_valid_values (__main__.AssetsDBTestSuite) ... ok
test_asset_statistics_by_tier (__main__.AssetsDBTestSuite) ... ok
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
   docker exec -it assets-db-test-e2e psql -U assets-admin -d assets-db
   ```
4. Clean up manually:
   ```bash
   docker stop assets-db-test-e2e
   docker rm assets-db-test-e2e
   docker rmi assets-db-test
   ```
