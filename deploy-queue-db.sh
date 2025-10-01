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

# Deployment script for queue-db microservice
# This script deploys the queue-db service to your local Kubernetes cluster

set -e

echo "🚀 Starting queue-db deployment..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed or not in PATH"
    exit 1
fi

# Check if cluster is accessible
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Kubernetes cluster is not accessible"
    echo "Please ensure your cluster is running and kubectl is configured"
    exit 1
fi

echo "✅ Kubernetes cluster is accessible"

# Navigate to the project root
cd "$(dirname "$0")"

# Method 1: Deploy using the main Kubernetes manifest
echo "📦 Deploying queue-db using Kubernetes manifest..."

# Apply the queue-db manifest
kubectl apply -f kubernetes-manifests/queue-db.yaml

echo "✅ queue-db manifest applied successfully"

# Wait for the StatefulSet to be ready
echo "⏳ Waiting for queue-db StatefulSet to be ready..."
kubectl wait --for=condition=ready pod -l app=queue-db --timeout=300s

echo "✅ queue-db StatefulSet is ready"

# Check the status
echo "📊 Checking deployment status..."
kubectl get pods -l app=queue-db
kubectl get services -l app=queue-db

# Show connection information
echo ""
echo "🔗 Connection Information:"
echo "   Service Name: queue-db"
echo "   Port: 5432"
echo "   Database: queue-db"
echo "   Username: queue-admin"
echo "   Password: queue-pwd"
echo "   Connection String: postgresql://queue-admin:queue-pwd@queue-db:5432/queue-db"

# Port forward for local access (optional)
echo ""
echo "🌐 Setting up port forwarding to localhost:5432..."
echo "   You can now connect to the database using:"
echo "   psql postgresql://queue-admin:queue-pwd@localhost:5432/queue-db"
echo ""
echo "   To stop port forwarding, press Ctrl+C"

# Start port forwarding in the background
kubectl port-forward service/queue-db 5432:5432 &
PORT_FORWARD_PID=$!

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping port forwarding..."
    kill $PORT_FORWARD_PID 2>/dev/null || true
    echo "✅ Port forwarding stopped"
    echo "🎉 queue-db deployment completed successfully!"
}

# Set trap to cleanup on script exit
trap cleanup EXIT INT TERM

# Wait for port forwarding to be ready
sleep 3

# Test database connection
echo "🧪 Testing database connection..."
if kubectl exec -it $(kubectl get pods -l app=queue-db -o jsonpath='{.items[0].metadata.name}') -- pg_isready -U queue-admin -d queue-db; then
    echo "✅ Database connection test successful"
else
    echo "❌ Database connection test failed"
    exit 1
fi

# Show useful commands
echo ""
echo "📋 Useful Commands:"
echo "   View logs: kubectl logs -f statefulset/queue-db"
echo "   Connect to DB: kubectl exec -it \$(kubectl get pods -l app=queue-db -o jsonpath='{.items[0].metadata.name}') -- psql -U queue-admin -d queue-db"
echo "   Check status: kubectl get pods -l app=queue-db"
echo "   Delete deployment: kubectl delete -f kubernetes-manifests/queue-db.yaml"

# Keep the script running to maintain port forwarding
echo ""
echo "🔄 Port forwarding is active. Press Ctrl+C to stop..."
wait $PORT_FORWARD_PID
