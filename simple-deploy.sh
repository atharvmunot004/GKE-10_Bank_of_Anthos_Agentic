#!/bin/bash

# Simple Bank of Anthos Deployment Script
# Uses your existing cluster: bank-of-anthos

set -e

PROJECT_ID="ffd-gke10"
REGION="us-central1"
CLUSTER_NAME="bank-of-anthos"

echo "🚀 Deploying Bank of Anthos to existing cluster: $CLUSTER_NAME"

# Get cluster credentials
echo "🔐 Getting cluster credentials..."
gcloud container clusters get-credentials $CLUSTER_NAME --region=$REGION

# Build and push images to Artifact Registry
echo "📦 Building and pushing container images..."

# Build and push all services
services=(
    "frontend"
    "accounts/contacts" 
    "accounts/userservice"
    "ledger/balancereader"
    "ledger/ledgerwriter"
    "ledger/transactionhistory"
    "accounts/accounts-db"
    "ledger/ledger-db"
    "loadgenerator"
    "investment-manager-svc"
    "invest-svc"
    "portfolio-reader-svc"
    "user-portfolio-db"
    "withdraw-svc"
    "user-request-queue-svc"
    "market-reader-svc"
    "execute-order-svc"
    "consistency-manager-svc"
    "user-tier-agent"
    "assets-db"
    "queue-db"
)

for service in "${services[@]}"; do
    echo "Building $service..."
    if [ -d "src/$service" ]; then
        cd "src/$service"
        
        # Build image
        docker build -t $REGION-docker.pkg.dev/$PROJECT_ID/bank-of-anthos/$service:latest .
        
        # Push to Artifact Registry
        docker push $REGION-docker.pkg.dev/$PROJECT_ID/bank-of-anthos/$service:latest
        
        cd ../..
        echo "✅ $service built and pushed"
    else
        echo "⚠️ Directory src/$service not found, skipping"
    fi
done

echo "🎉 All images built and pushed successfully!"
echo "📋 Next steps:"
echo "1. Deploy services using kubectl or Skaffold"
echo "2. Set up GitHub Actions for automated deployment"
echo "3. Configure monitoring and logging"

echo "🔗 Your Artifact Registry: https://console.cloud.google.com/artifacts/docker/$PROJECT_ID/$REGION/bank-of-anthos"
