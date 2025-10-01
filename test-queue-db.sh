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

# Comprehensive testing script for queue-db microservice
# This script deploys the service, runs all tests, and provides detailed reports

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Default values
DEPLOY_SERVICE=true
RUN_TESTS=true
RUN_LOAD_TESTS=false
CLEANUP=true
VERBOSE=false
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

print_test() {
    echo -e "${PURPLE}[TEST]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --no-deploy          Skip service deployment"
    echo "  --no-tests           Skip unit/integration tests"
    echo "  --load-tests         Run load tests"
    echo "  --no-cleanup         Skip cleanup after tests"
    echo "  -v, --verbose        Verbose output"
    echo "  -r, --report-dir DIR Report directory (default: ./test-reports)"
    echo "  -h, --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                           # Full test suite"
    echo "  $0 --no-deploy --load-tests  # Load tests only"
    echo "  $0 --no-tests --load-tests   # Deploy and load test only"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-deploy)
            DEPLOY_SERVICE=false
            shift
            ;;
        --no-tests)
            RUN_TESTS=false
            shift
            ;;
        --load-tests)
            RUN_LOAD_TESTS=true
            shift
            ;;
        --no-cleanup)
            CLEANUP=false
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
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

# Create report directory
mkdir -p "$REPORT_DIR"

print_status "Starting comprehensive queue-db testing..."
print_status "Deploy service: $DEPLOY_SERVICE"
print_status "Run tests: $RUN_TESTS"
print_status "Run load tests: $RUN_LOAD_TESTS"
print_status "Cleanup: $CLEANUP"
print_status "Report directory: $REPORT_DIR"

# Check prerequisites
print_status "Checking prerequisites..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed or not in PATH"
    exit 1
fi

# Check if cluster is accessible
if ! kubectl cluster-info &> /dev/null; then
    print_error "Kubernetes cluster is not accessible"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed or not in PATH"
    exit 1
fi

print_success "Prerequisites check passed"

# Deploy service if requested
if [ "$DEPLOY_SERVICE" = true ]; then
    print_status "Deploying queue-db service..."
    
    # Apply the Kubernetes manifest
    kubectl apply -f kubernetes-manifests/queue-db.yaml
    
    # Wait for deployment to be ready
    print_status "Waiting for queue-db StatefulSet to be ready..."
    kubectl wait --for=condition=ready pod -l app=queue-db --timeout=300s
    
    print_success "Queue-db service deployed successfully"
    
    # Set up port forwarding
    print_status "Setting up port forwarding..."
    kubectl port-forward service/queue-db 5432:5432 &
    PORT_FORWARD_PID=$!
    
    # Wait for port forwarding to be ready
    sleep 5
    
    print_success "Port forwarding established on localhost:5432"
fi

# Run unit and integration tests if requested
if [ "$RUN_TESTS" = true ]; then
    print_test "Running unit and integration tests..."
    
    # Navigate to queue-db directory
    cd src/queue-db
    
    # Install test dependencies
    print_status "Installing test dependencies..."
    pip install -r tests/requirements.txt
    
    # Set environment variables
    export TEST_QUEUE_DB_URI="postgresql://queue-admin:queue-pwd@localhost:5432/queue-db"
    
    # Run tests
    print_status "Running tests..."
    if ./run_tests.sh -c -r "$REPORT_DIR"; then
        print_success "All tests passed!"
    else
        print_error "Tests failed!"
        if [ "$CLEANUP" = true ]; then
            cleanup_and_exit
        fi
        exit 1
    fi
    
    # Return to project root
    cd ../..
fi

# Run load tests if requested
if [ "$RUN_LOAD_TESTS" = true ]; then
    print_test "Running load tests..."
    
    # Check if Locust is installed
    if ! command -v locust &> /dev/null; then
        print_status "Installing Locust..."
        pip install locust
    fi
    
    # Navigate to queue-db directory
    cd src/queue-db
    
    # Run load tests
    print_status "Starting load tests..."
    print_status "Load test will run for 60 seconds with 10 users"
    print_status "Access Locust web UI at http://localhost:8089"
    
    # Run Locust in headless mode
    locust -f tests/load/locustfile.py \
        --host=localhost:5432 \
        --users=10 \
        --spawn-rate=2 \
        --run-time=60s \
        --headless \
        --html="$REPORT_DIR/load-test-report.html" \
        --csv="$REPORT_DIR/load-test" || true
    
    print_success "Load tests completed"
    
    # Return to project root
    cd ../..
fi

# Generate comprehensive test report
print_status "Generating comprehensive test report..."

cat > "$REPORT_DIR/test-summary.md" << EOF
# Queue-DB Test Summary

## Test Execution Details
- **Date**: $(date)
- **Service Deployed**: $DEPLOY_SERVICE
- **Unit/Integration Tests**: $RUN_TESTS
- **Load Tests**: $RUN_LOAD_TESTS
- **Cleanup**: $CLEANUP

## Test Results

### Unit and Integration Tests
EOF

if [ "$RUN_TESTS" = true ]; then
    if [ -f "$REPORT_DIR/junit.xml" ]; then
        echo "- **Status**: ✅ Passed" >> "$REPORT_DIR/test-summary.md"
        echo "- **Report**: [HTML Report]($(basename "$REPORT_DIR")/report.html)" >> "$REPORT_DIR/test-summary.md"
        echo "- **Coverage**: [Coverage Report]($(basename "$REPORT_DIR")/coverage/index.html)" >> "$REPORT_DIR/test-summary.md"
    else
        echo "- **Status**: ❌ Failed or Not Run" >> "$REPORT_DIR/test-summary.md"
    fi
else
    echo "- **Status**: ⏭️ Skipped" >> "$REPORT_DIR/test-summary.md"
fi

cat >> "$REPORT_DIR/test-summary.md" << EOF

### Load Tests
EOF

if [ "$RUN_LOAD_TESTS" = true ]; then
    if [ -f "$REPORT_DIR/load-test-report.html" ]; then
        echo "- **Status**: ✅ Completed" >> "$REPORT_DIR/test-summary.md"
        echo "- **Report**: [Load Test Report]($(basename "$REPORT_DIR")/load-test-report.html)" >> "$REPORT_DIR/test-summary.md"
    else
        echo "- **Status**: ❌ Failed or Not Run" >> "$REPORT_DIR/test-summary.md"
    fi
else
    echo "- **Status**: ⏭️ Skipped" >> "$REPORT_DIR/test-summary.md"
fi

cat >> "$REPORT_DIR/test-summary.md" << EOF

## Service Status
EOF

if [ "$DEPLOY_SERVICE" = true ]; then
    echo "- **Deployment**: ✅ Deployed" >> "$REPORT_DIR/test-summary.md"
    echo "- **Pods**: \`kubectl get pods -l app=queue-db\`" >> "$REPORT_DIR/test-summary.md"
    echo "- **Services**: \`kubectl get services -l app=queue-db\`" >> "$REPORT_DIR/test-summary.md"
else
    echo "- **Deployment**: ⏭️ Skipped" >> "$REPORT_DIR/test-summary.md"
fi

cat >> "$REPORT_DIR/test-summary.md" << EOF

## Next Steps
1. Review test reports in the \`$(basename "$REPORT_DIR")\` directory
2. Check service logs: \`kubectl logs -f statefulset/queue-db\`
3. Monitor service metrics: \`kubectl top pod -l app=queue-db\`
4. Clean up resources if needed: \`kubectl delete -f kubernetes-manifests/queue-db.yaml\`

## Troubleshooting
- Check service status: \`kubectl get pods -l app=queue-db\`
- View service logs: \`kubectl logs -f statefulset/queue-db\`
- Test database connection: \`kubectl exec -it \$(kubectl get pods -l app=queue-db -o jsonpath='{.items[0].metadata.name}') -- psql -U queue-admin -d queue-db\`
EOF

print_success "Test summary generated: $REPORT_DIR/test-summary.md"

# Show test results summary
print_status "Test Results Summary:"
echo "========================"

if [ "$RUN_TESTS" = true ]; then
    if [ -f "$REPORT_DIR/junit.xml" ]; then
        print_success "✅ Unit/Integration Tests: PASSED"
    else
        print_error "❌ Unit/Integration Tests: FAILED"
    fi
else
    print_warning "⏭️ Unit/Integration Tests: SKIPPED"
fi

if [ "$RUN_LOAD_TESTS" = true ]; then
    if [ -f "$REPORT_DIR/load-test-report.html" ]; then
        print_success "✅ Load Tests: COMPLETED"
    else
        print_error "❌ Load Tests: FAILED"
    fi
else
    print_warning "⏭️ Load Tests: SKIPPED"
fi

print_status "Reports available in: $REPORT_DIR/"

# Cleanup function
cleanup_and_exit() {
    print_status "Cleaning up..."
    
    # Stop port forwarding
    if [ -n "$PORT_FORWARD_PID" ]; then
        kill $PORT_FORWARD_PID 2>/dev/null || true
        print_status "Port forwarding stopped"
    fi
    
    # Clean up Kubernetes resources if requested
    if [ "$CLEANUP" = true ]; then
        print_status "Cleaning up Kubernetes resources..."
        kubectl delete -f kubernetes-manifests/queue-db.yaml || true
        print_status "Kubernetes resources cleaned up"
    fi
    
    print_success "Cleanup completed"
}

# Set trap for cleanup on exit
trap cleanup_and_exit EXIT INT TERM

# Keep script running if port forwarding is active
if [ "$DEPLOY_SERVICE" = true ] && [ "$CLEANUP" = false ]; then
    print_status "Service is running. Press Ctrl+C to stop and cleanup."
    print_status "Database available at: postgresql://queue-admin:queue-pwd@localhost:5432/queue-db"
    
    # Wait for user interrupt
    wait $PORT_FORWARD_PID
else
    print_success "Testing completed successfully!"
fi
