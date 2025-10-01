#!/bin/bash

# Deploy user-request-queue-svc to GKE
# This script builds, pushes, and deploys the microservice

set -e

# Configuration
PROJECT_ID="bank-of-anthos-ci"
REGION="us-central1"
SERVICE_NAME="user-request-queue-svc"
IMAGE_TAG="v1.0.0"
REGISTRY="us-central1-docker.pkg.dev"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting deployment of ${SERVICE_NAME}${NC}"

# Step 1: Build Docker image
echo -e "${YELLOW}Step 1: Building Docker image${NC}"
cd src/user-request-queue-svc
docker build -t ${REGISTRY}/${PROJECT_ID}/bank-of-anthos/${SERVICE_NAME}:${IMAGE_TAG} .
docker build -t ${REGISTRY}/${PROJECT_ID}/bank-of-anthos/${SERVICE_NAME}:latest .

# Step 2: Push to registry
echo -e "${YELLOW}Step 2: Pushing image to registry${NC}"
docker push ${REGISTRY}/${PROJECT_ID}/bank-of-anthos/${SERVICE_NAME}:${IMAGE_TAG}
docker push ${REGISTRY}/${PROJECT_ID}/bank-of-anthos/${SERVICE_NAME}:latest

# Step 3: Deploy to Kubernetes
echo -e "${YELLOW}Step 3: Deploying to Kubernetes${NC}"
cd ../../kubernetes-manifests
kubectl apply -f user-request-queue-svc.yaml

# Step 4: Wait for deployment
echo -e "${YELLOW}Step 4: Waiting for deployment to be ready${NC}"
kubectl wait --for=condition=available --timeout=300s deployment/${SERVICE_NAME}

# Step 5: Verify deployment
echo -e "${YELLOW}Step 5: Verifying deployment${NC}"
kubectl get pods -l app=${SERVICE_NAME}
kubectl get services -l app=${SERVICE_NAME}

# Step 6: Test health endpoint
echo -e "${YELLOW}Step 6: Testing health endpoint${NC}"
SERVICE_IP=$(kubectl get service ${SERVICE_NAME} -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
if [ -z "$SERVICE_IP" ]; then
    SERVICE_IP=$(kubectl get service ${SERVICE_NAME} -o jsonpath='{.spec.clusterIP}')
fi

echo "Service IP: ${SERVICE_IP}"
echo "Testing health endpoint..."
kubectl run test-pod --image=curlimages/curl --rm -i --restart=Never -- curl -f http://${SERVICE_IP}:8080/health

echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}Service is available at: http://${SERVICE_IP}:8080${NC}"
echo -e "${GREEN}Health check: http://${SERVICE_IP}:8080/health${NC}"
echo -e "${GREEN}Metrics: http://${SERVICE_IP}:8080/metrics${NC}"
