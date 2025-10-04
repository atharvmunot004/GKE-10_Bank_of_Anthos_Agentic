#!/bin/bash

# User Tier Agent Deployment Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="user-tier-agent"
VERSION="v1.0.0"
REGISTRY="localhost:5000"
FULL_IMAGE_NAME="${REGISTRY}/${IMAGE_NAME}:${VERSION}"
NAMESPACE="bank-of-anthos"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    
    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed. Please install kubectl and try again."
        exit 1
    fi
    
    # Check if cluster is accessible
    if ! kubectl cluster-info > /dev/null 2>&1; then
        log_error "Kubernetes cluster is not accessible. Please check your kubeconfig."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

build_image() {
    log_info "Building Docker image..."
    
    # Build the image
    if docker build -t ${FULL_IMAGE_NAME} .; then
        log_success "Docker image built successfully"
    else
        log_error "Failed to build Docker image"
        exit 1
    fi
}

push_image() {
    log_info "Pushing Docker image to registry..."
    
    # Push the image
    if docker push ${FULL_IMAGE_NAME}; then
        log_success "Docker image pushed successfully"
    else
        log_error "Failed to push Docker image"
        exit 1
    fi
}

deploy_to_kubernetes() {
    log_info "Deploying to Kubernetes..."
    
    # Create namespace if it doesn't exist
    kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
    
    # Apply the manifest
    if kubectl apply -f ../../kubernetes-manifests/user-tier-agent.yaml -n ${NAMESPACE}; then
        log_success "Kubernetes manifest applied successfully"
    else
        log_error "Failed to apply Kubernetes manifest"
        exit 1
    fi
}

wait_for_deployment() {
    log_info "Waiting for deployment to be ready..."
    
    # Wait for deployment to be ready
    if kubectl wait --for=condition=available --timeout=300s deployment/user-tier-agent -n ${NAMESPACE}; then
        log_success "Deployment is ready"
    else
        log_error "Deployment failed to become ready"
        exit 1
    fi
}

run_tests() {
    log_info "Running post-deployment tests..."
    
    # Get the service URL
    SERVICE_URL=$(kubectl get service user-tier-agent -n ${NAMESPACE} -o jsonpath='{.spec.clusterIP}:{.spec.ports[0].port}')
    
    # Wait for the service to be ready
    log_info "Waiting for service to be ready..."
    sleep 30
    
    # Test health endpoint
    if kubectl run test-pod --image=curlimages/curl --rm -i --restart=Never -- curl -f http://${SERVICE_URL}/health; then
        log_success "Health check passed"
    else
        log_warning "Health check failed, but continuing..."
    fi
    
    # Test readiness endpoint
    if kubectl run test-pod --image=curlimages/curl --rm -i --restart=Never -- curl -f http://${SERVICE_URL}/ready; then
        log_success "Readiness check passed"
    else
        log_warning "Readiness check failed, but continuing..."
    fi
}

show_status() {
    log_info "Deployment status:"
    
    echo ""
    echo "Pods:"
    kubectl get pods -l app=user-tier-agent -n ${NAMESPACE}
    
    echo ""
    echo "Services:"
    kubectl get svc -l app=user-tier-agent -n ${NAMESPACE}
    
    echo ""
    echo "Deployment:"
    kubectl get deployment user-tier-agent -n ${NAMESPACE}
    
    echo ""
    echo "HPA:"
    kubectl get hpa user-tier-agent -n ${NAMESPACE}
}

cleanup() {
    log_info "Cleaning up..."
    
    # Remove the deployment
    kubectl delete -f ../../kubernetes-manifests/user-tier-agent.yaml -n ${NAMESPACE} --ignore-not-found=true
    
    log_success "Cleanup completed"
}

# Main script
main() {
    case "${1:-deploy}" in
        "deploy")
            check_prerequisites
            build_image
            push_image
            deploy_to_kubernetes
            wait_for_deployment
            run_tests
            show_status
            log_success "Deployment completed successfully!"
            ;;
        "undeploy")
            cleanup
            log_success "Undeployment completed successfully!"
            ;;
        "status")
            show_status
            ;;
        "test")
            run_tests
            ;;
        "build")
            check_prerequisites
            build_image
            ;;
        "push")
            check_prerequisites
            push_image
            ;;
        *)
            echo "Usage: $0 {deploy|undeploy|status|test|build|push}"
            echo ""
            echo "Commands:"
            echo "  deploy   - Build, push, and deploy the application"
            echo "  undeploy - Remove the application from Kubernetes"
            echo "  status   - Show deployment status"
            echo "  test     - Run post-deployment tests"
            echo "  build    - Build Docker image only"
            echo "  push     - Push Docker image only"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
