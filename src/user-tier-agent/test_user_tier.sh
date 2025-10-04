#!/bin/bash

# User Tier Agent Complete Testing Script
# This script performs comprehensive testing of the user-tier-agent microservice

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
SERVICE_NAME="user-tier-agent"
TEST_TIMEOUT=300
HEALTH_CHECK_TIMEOUT=60

# Test results
TESTS_PASSED=0
TESTS_FAILED=0
TOTAL_TESTS=0

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    ((TESTS_PASSED++))
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    ((TESTS_FAILED++))
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

log_test() {
    echo -e "${CYAN}[TEST]${NC} $1"
    ((TOTAL_TESTS++))
}

# Cleanup function
cleanup() {
    log_step "Starting cleanup process..."
    
    # Stop Docker Compose
    if [ -f "docker-compose.yml" ]; then
        log_info "Stopping Docker Compose services..."
        docker-compose down -v --remove-orphans 2>/dev/null || true
    fi
    
    # Kill processes
    log_info "Stopping running processes..."
    pkill -f "user-tier-agent" 2>/dev/null || true
    pkill -f "uvicorn.*8080" 2>/dev/null || true
    pkill -f "python.*main.py" 2>/dev/null || true
    
    # Free ports
    log_info "Freeing ports..."
    for port in 8080 6379 8081 8082 8083; do
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
    done
    
    # Clean Docker resources
    log_info "Cleaning Docker resources..."
    docker stop $(docker ps -q --filter "name=user-tier-agent" --filter "name=redis" --filter "name=mock-") 2>/dev/null || true
    docker rm $(docker ps -aq --filter "name=user-tier-agent" --filter "name=redis" --filter "name=mock-") 2>/dev/null || true
    
    # Clean test artifacts
    log_info "Cleaning test artifacts..."
    rm -rf tests/__pycache__/ app/__pycache__/ .pytest_cache/ htmlcov/ .coverage load_test_results/ *.log .env 2>/dev/null || true
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    
    log_success "Cleanup completed successfully"
}

# Environment setup
setup_environment() {
    log_step "Setting up testing environment..."
    
    # Navigate to service directory
    cd "$SCRIPT_DIR"
    
    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        log_info "Creating .env file..."
        cp env.example .env
        # Set a dummy API key for testing
        echo "GOOGLE_API_KEY=test-api-key-for-testing" >> .env
    fi
    
    # Install dependencies
    log_info "Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt || {
        log_warning "Some dependencies failed to install, continuing with available packages..."
    }
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    
    # Build Docker image
    log_info "Building Docker image..."
    docker build -t user-tier-agent:test .
    
    log_success "Environment setup completed"
}

# Health check function
wait_for_health() {
    local url=$1
    local timeout=${2:-$HEALTH_CHECK_TIMEOUT}
    local count=0
    
    log_info "Waiting for service to be healthy at $url..."
    
    while [ $count -lt $timeout ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            log_success "Service is healthy"
            return 0
        fi
        sleep 2
        ((count += 2))
    done
    
    log_error "Service failed to become healthy within ${timeout}s"
    return 1
}

# Functional tests
test_health_endpoints() {
    log_test "Testing health endpoints..."
    
    # Test health endpoint
    if curl -f -s "http://localhost:8080/health" | grep -q "healthy"; then
        log_success "Health endpoint test passed"
    else
        log_error "Health endpoint test failed"
        return 1
    fi
    
    # Test readiness endpoint
    if curl -f -s "http://localhost:8080/ready" | grep -q "ready"; then
        log_success "Readiness endpoint test passed"
    else
        log_error "Readiness endpoint test failed"
        return 1
    fi
    
    # Test metrics endpoint
    if curl -f -s "http://localhost:8080/metrics" | grep -q "http_requests_total"; then
        log_success "Metrics endpoint test passed"
    else
        log_error "Metrics endpoint test failed"
        return 1
    fi
}

test_api_endpoints() {
    log_test "Testing API endpoints..."
    
    # Test tier allocation with INVEST
    local response=$(curl -s -X POST "http://localhost:8080/api/v1/allocation/allocate-tiers" \
        -H "Content-Type: application/json" \
        -d '{
            "uuid": "123e4567-e89b-12d3-a456-426614174000",
            "accountid": "test-account-123",
            "amount": 10000.0,
            "purpose": "INVEST"
        }')
    
    if echo "$response" | grep -q '"success":true'; then
        log_success "INVEST allocation test passed"
    else
        log_error "INVEST allocation test failed: $response"
        return 1
    fi
    
    # Test tier allocation with WITHDRAW
    local response=$(curl -s -X POST "http://localhost:8080/api/v1/allocation/allocate-tiers" \
        -H "Content-Type: application/json" \
        -d '{
            "uuid": "123e4567-e89b-12d3-a456-426614174001",
            "accountid": "test-account-456",
            "amount": 5000.0,
            "purpose": "WITHDRAW"
        }')
    
    if echo "$response" | grep -q '"success":true'; then
        log_success "WITHDRAW allocation test passed"
    else
        log_error "WITHDRAW allocation test failed: $response"
        return 1
    fi
    
    # Test default allocation
    local response=$(curl -s "http://localhost:8080/api/v1/allocation/allocate-tiers/new-user-123/default?amount=3000.0")
    
    if echo "$response" | grep -q '"success":true'; then
        log_success "Default allocation test passed"
    else
        log_error "Default allocation test failed: $response"
        return 1
    fi
}

test_validation() {
    log_test "Testing request validation..."
    
    # Test invalid UUID
    local response=$(curl -s -X POST "http://localhost:8080/api/v1/allocation/allocate-tiers" \
        -H "Content-Type: application/json" \
        -d '{"uuid": "invalid", "accountid": "test", "amount": 1000, "purpose": "INVEST"}')
    
    if echo "$response" | grep -q "400"; then
        log_success "Invalid UUID validation test passed"
    else
        log_error "Invalid UUID validation test failed: $response"
        return 1
    fi
    
    # Test negative amount
    local response=$(curl -s -X POST "http://localhost:8080/api/v1/allocation/allocate-tiers" \
        -H "Content-Type: application/json" \
        -d '{"uuid": "123e4567-e89b-12d3-a456-426614174000", "accountid": "test", "amount": -1000, "purpose": "INVEST"}')
    
    if echo "$response" | grep -q "400"; then
        log_success "Negative amount validation test passed"
    else
        log_error "Negative amount validation test failed: $response"
        return 1
    fi
}

test_performance() {
    log_test "Testing performance..."
    
    local start_time=$(date +%s)
    local success_count=0
    
    # Test 10 concurrent requests
    for i in {1..10}; do
        (
            local response=$(curl -s -X POST "http://localhost:8080/api/v1/allocation/allocate-tiers" \
                -H "Content-Type: application/json" \
                -d "{\"uuid\":\"$(uuidgen)\",\"accountid\":\"test-account-123\",\"amount\":10000.0,\"purpose\":\"INVEST\"}")
            if echo "$response" | grep -q '"success":true'; then
                echo "1" > /tmp/test_result_$i
            else
                echo "0" > /tmp/test_result_$i
            fi
        ) &
    done
    
    # Wait for all requests to complete
    wait
    
    # Count successful requests
    for i in {1..10}; do
        if [ -f "/tmp/test_result_$i" ]; then
            local result=$(cat "/tmp/test_result_$i")
            if [ "$result" = "1" ]; then
                ((success_count++))
            fi
            rm -f "/tmp/test_result_$i"
        fi
    done
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    if [ $success_count -ge 8 ]; then
        log_success "Performance test passed ($success_count/10 requests successful in ${duration}s)"
    else
        log_error "Performance test failed ($success_count/10 requests successful in ${duration}s)"
        return 1
    fi
}

# Unit tests
run_unit_tests() {
    log_test "Running unit tests..."
    
    if [ -f "tests/unit/test_config.py" ]; then
        if python -m pytest tests/unit/ -v --tb=short; then
            log_success "Unit tests passed"
        else
            log_error "Unit tests failed"
            return 1
        fi
    else
        log_warning "Unit tests not found, skipping..."
    fi
}

# Integration tests
run_integration_tests() {
    log_test "Running integration tests..."
    
    if [ -f "tests/integration/test_integration_api.py" ]; then
        if python -m pytest tests/integration/ -v --tb=short; then
            log_success "Integration tests passed"
        else
            log_error "Integration tests failed"
            return 1
        fi
    else
        log_warning "Integration tests not found, skipping..."
    fi
}

# Docker tests
test_docker_services() {
    log_test "Testing Docker services..."
    
    # Start services
    log_info "Starting Docker Compose services..."
    docker-compose up -d
    
    # Wait for services to be ready
    wait_for_health "http://localhost:8080/health" 60
    
    # Test service communication
    local response=$(curl -s "http://localhost:8080/health")
    if echo "$response" | grep -q "healthy"; then
        log_success "Docker services test passed"
    else
        log_error "Docker services test failed: $response"
        return 1
    fi
}

# Main test execution
run_all_tests() {
    log_step "Starting comprehensive testing of user-tier-agent..."
    
    # Setup environment
    setup_environment
    
    # Start services with Docker Compose
    log_info "Starting services with Docker Compose..."
    docker-compose up -d
    
    # Wait for services to be ready
    if ! wait_for_health "http://localhost:8080/health" 60; then
        log_error "Services failed to start properly"
        return 1
    fi
    
    # Run all tests
    log_step "Running comprehensive test suite..."
    
    # Functional tests
    test_health_endpoints
    test_api_endpoints
    test_validation
    test_performance
    
    # Automated tests
    run_unit_tests
    run_integration_tests
    
    # Docker tests
    test_docker_services
    
    # Print test summary
    log_step "Test Summary"
    echo -e "${GREEN}Tests Passed: $TESTS_PASSED${NC}"
    echo -e "${RED}Tests Failed: $TESTS_FAILED${NC}"
    echo -e "${BLUE}Total Tests: $TOTAL_TESTS${NC}"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        log_success "All tests completed successfully!"
        return 0
    else
        log_error "Some tests failed!"
        return 1
    fi
}

# Main execution
main() {
    echo -e "${PURPLE}========================================${NC}"
    echo -e "${PURPLE}  User Tier Agent Testing Script${NC}"
    echo -e "${PURPLE}========================================${NC}"
    echo
    
    # Trap cleanup on exit
    trap cleanup EXIT
    
    # Run tests
    if run_all_tests; then
        echo
        log_success "🎉 All tests completed successfully!"
        exit 0
    else
        echo
        log_error "❌ Some tests failed!"
        exit 1
    fi
}

# Execute main function
main "$@"
