#!/bin/bash
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

# Test runner script for queue-db microservice
# This script runs unit tests, integration tests, and performance tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
TEST_TYPE="all"
VERBOSE=false
COVERAGE=false
PARALLEL=false
REPORT_DIR="./test-reports"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -t, --type TYPE        Test type: unit, integration, performance, all (default: all)"
    echo "  -v, --verbose          Verbose output"
    echo "  -c, --coverage         Generate coverage report"
    echo "  -p, --parallel         Run tests in parallel"
    echo "  -r, --report-dir DIR   Report directory (default: ./test-reports)"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                     # Run all tests"
    echo "  $0 -t unit             # Run only unit tests"
    echo "  $0 -t integration -c   # Run integration tests with coverage"
    echo "  $0 -t performance -p   # Run performance tests in parallel"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -p|--parallel)
            PARALLEL=true
            shift
            ;;
        -r|--report-dir)
            REPORT_DIR="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate test type
case $TEST_TYPE in
    unit|integration|performance|all)
        ;;
    *)
        print_error "Invalid test type: $TEST_TYPE"
        show_usage
        exit 1
        ;;
esac

# Create report directory
mkdir -p "$REPORT_DIR"

# Build pytest command
PYTEST_CMD="pytest"

# Add verbosity
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

# Add coverage
if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=src --cov-report=html:$REPORT_DIR/coverage --cov-report=xml:$REPORT_DIR/coverage.xml"
fi

# Add parallel execution
if [ "$PARALLEL" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -n auto"
fi

# Add test directory based on type
case $TEST_TYPE in
    unit)
        PYTEST_CMD="$PYTEST_CMD tests/unit/"
        ;;
    integration)
        PYTEST_CMD="$PYTEST_CMD tests/integration/"
        ;;
    performance)
        PYTEST_CMD="$PYTEST_CMD tests/integration/ -m performance"
        ;;
    all)
        PYTEST_CMD="$PYTEST_CMD tests/"
        ;;
esac

# Add HTML report
PYTEST_CMD="$PYTEST_CMD --html=$REPORT_DIR/report.html --self-contained-html"

# Add JUnit XML report
PYTEST_CMD="$PYTEST_CMD --junitxml=$REPORT_DIR/junit.xml"

print_status "Starting $TEST_TYPE tests..."
print_status "Command: $PYTEST_CMD"
print_status "Report directory: $REPORT_DIR"

# Check if test dependencies are installed
print_status "Checking test dependencies..."
if ! python -c "import pytest" 2>/dev/null; then
    print_error "pytest is not installed. Installing test dependencies..."
    pip install -r tests/requirements.txt
fi

# Run tests
print_status "Running tests..."
if eval $PYTEST_CMD; then
    print_success "All tests passed!"
    
    if [ "$COVERAGE" = true ]; then
        print_success "Coverage report generated in $REPORT_DIR/coverage/"
    fi
    
    print_success "Test reports generated in $REPORT_DIR/"
    print_status "HTML report: $REPORT_DIR/report.html"
    print_status "JUnit XML: $REPORT_DIR/junit.xml"
    
    exit 0
else
    print_error "Tests failed!"
    print_status "Check the reports in $REPORT_DIR/ for details"
    exit 1
fi
