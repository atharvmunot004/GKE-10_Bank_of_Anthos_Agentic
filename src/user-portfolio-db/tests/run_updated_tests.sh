#!/bin/bash
# Updated test runner script for User Portfolio Database

set -e

echo "=========================================="
echo "User Portfolio Database Updated Tests"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2${NC}"
    else
        echo -e "${RED}✗ $2${NC}"
    fi
}

# Function to run the updated test
run_updated_test() {
    local test_file=$1
    local test_name=$2
    
    echo -e "\n${YELLOW}Running $test_name...${NC}"
    
    # Try different connection methods
    if [ -n "$DATABASE_URL" ]; then
        # Use DATABASE_URL if available
        if psql "$DATABASE_URL" -f "$test_file" > /dev/null 2>&1; then
            print_status 0 "$test_name"
            return 0
        else
            print_status 1 "$test_name"
            return 1
        fi
    elif [ -n "$PGHOST" ]; then
        # Use environment variables
        if psql -h "$PGHOST" -p "${PGPORT:-5432}" -U "${PGUSER:-postgres}" -d "${PGDATABASE:-postgres}" -f "$test_file" > /dev/null 2>&1; then
            print_status 0 "$test_name"
            return 0
        else
            print_status 1 "$test_name"
            return 1
        fi
    else
        # Try local connection
        if psql -h localhost -p 5432 -U postgres -d postgres -f "$test_file" > /dev/null 2>&1; then
            print_status 0 "$test_name"
            return 0
        else
            print_status 1 "$test_name"
            return 1
        fi
    fi
}

# Check if PostgreSQL client is available
if ! command -v psql &> /dev/null; then
    echo -e "${RED}PostgreSQL client (psql) is not installed or not in PATH${NC}"
    echo "Please install PostgreSQL client tools"
    exit 1
fi

# Check if we can connect to a database
echo -e "${BLUE}Checking database connection...${NC}"

if [ -n "$DATABASE_URL" ]; then
    echo "Using DATABASE_URL for connection"
    if ! psql "$DATABASE_URL" -c "SELECT 1;" > /dev/null 2>&1; then
        echo -e "${RED}Cannot connect to database using DATABASE_URL${NC}"
        exit 1
    fi
elif [ -n "$PGHOST" ]; then
    echo "Using environment variables for connection"
    if ! psql -h "$PGHOST" -p "${PGPORT:-5432}" -U "${PGUSER:-postgres}" -d "${PGDATABASE:-postgres}" -c "SELECT 1;" > /dev/null 2>&1; then
        echo -e "${RED}Cannot connect to database using environment variables${NC}"
        exit 1
    fi
else
    echo "Trying local connection (localhost:5432)"
    if ! psql -h localhost -p 5432 -U postgres -d postgres -c "SELECT 1;" > /dev/null 2>&1; then
        echo -e "${RED}Cannot connect to local database${NC}"
        echo "Please ensure PostgreSQL is running and accessible"
        echo "Or set DATABASE_URL or PGHOST environment variables"
        exit 1
    fi
fi

echo -e "${GREEN}Database connection successful!${NC}"

# Check if test database exists, if not create it
TEST_DB="test_user_portfolio_db"
echo -e "\n${BLUE}Setting up test database...${NC}"

if [ -n "$DATABASE_URL" ]; then
    # Extract database name from DATABASE_URL and create test database
    DB_NAME=$(echo "$DATABASE_URL" | sed -n 's/.*\/\([^?]*\).*/\1/p')
    if [ -z "$DB_NAME" ]; then
        DB_NAME="postgres"
    fi
    # Create test database
    psql "$DATABASE_URL" -c "DROP DATABASE IF EXISTS $TEST_DB;" 2>/dev/null || true
    psql "$DATABASE_URL" -c "CREATE DATABASE $TEST_DB;" 2>/dev/null || true
    TEST_DATABASE_URL=$(echo "$DATABASE_URL" | sed "s|/$DB_NAME|/$TEST_DB|")
else
    # Create test database using environment variables or defaults
    PGHOST=${PGHOST:-localhost}
    PGPORT=${PGPORT:-5432}
    PGUSER=${PGUSER:-postgres}
    
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres -c "DROP DATABASE IF EXISTS $TEST_DB;" 2>/dev/null || true
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres -c "CREATE DATABASE $TEST_DB;" 2>/dev/null || true
fi

# Load schema into test database
echo -e "${BLUE}Loading database schema...${NC}"
if [ -n "$TEST_DATABASE_URL" ]; then
    psql "$TEST_DATABASE_URL" -f ../initdb/0-user-portfolio-schema.sql
else
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$TEST_DB" -f ../initdb/0-user-portfolio-schema.sql
fi

# Run the updated test
echo -e "\n${YELLOW}Starting test execution...${NC}"

failed_tests=0
total_tests=1

# Run the comprehensive updated test
if [ -n "$TEST_DATABASE_URL" ]; then
    if ! psql "$TEST_DATABASE_URL" -f "test_user_portfolio_db_updated.sql" > /dev/null 2>&1; then
        failed_tests=$((failed_tests + 1))
    fi
else
    if ! psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$TEST_DB" -f "test_user_portfolio_db_updated.sql" > /dev/null 2>&1; then
        failed_tests=$((failed_tests + 1))
    fi
fi

if [ $failed_tests -eq 0 ]; then
    print_status 0 "Comprehensive Database Tests"
else
    print_status 1 "Comprehensive Database Tests"
fi

# Summary
echo -e "\n=========================================="
echo "Test Summary"
echo "=========================================="
echo "Total Tests: $total_tests"
echo "Passed: $((total_tests - failed_tests))"
echo "Failed: $failed_tests"

if [ $failed_tests -eq 0 ]; then
    echo -e "${GREEN}All tests passed! 🎉${NC}"
    echo -e "${GREEN}User Portfolio Database is working correctly!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please check the output above.${NC}"
    exit 1
fi
