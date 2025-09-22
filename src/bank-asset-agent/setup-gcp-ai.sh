#!/bin/bash
# Copyright 2024 Google LLC
# Bank Asset Agent - GCP AI Setup Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=""
SERVICE_ACCOUNT_NAME="bank-asset-agent-sa"
KEY_FILE="bank-asset-agent-key.json"
NAMESPACE="default"
CLUSTER_NAME=""
ZONE=""
REGION=""
USE_EXISTING_SA=false
EXISTING_SA_EMAIL=""

echo -e "${BLUE}🚀 Bank Asset Agent - GCP AI Setup${NC}"
echo "=========================================="
echo -e "${CYAN}This script will set up Gemini AI integration for the Bank Asset Agent${NC}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to display project information
display_project_info() {
    echo -e "${CYAN}📊 Current GCP Project Information${NC}"
    echo "=================================="
    
    # Current project
    CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "None")
    echo -e "${YELLOW}Current Project:${NC} $CURRENT_PROJECT"
    
    # All projects
    echo -e "\n${YELLOW}Available Projects:${NC}"
    gcloud projects list --format="table(projectId,name,projectNumber,lifecycleState)" 2>/dev/null || echo "Unable to list projects"
    
    # GKE clusters
    echo -e "\n${YELLOW}Available GKE Clusters:${NC}"
    gcloud container clusters list --format="table(name,location,status,currentMasterVersion,currentNodeVersion)" 2>/dev/null || echo "No clusters found or unable to list clusters"
    
    # Enabled APIs
    echo -e "\n${YELLOW}Currently Enabled APIs:${NC}"
    gcloud services list --enabled --format="table(name,title)" 2>/dev/null | head -10 || echo "Unable to list APIs"
    
    # Service accounts
    echo -e "\n${YELLOW}Existing Service Accounts:${NC}"
    gcloud iam service-accounts list --format="table(email,displayName,disabled)" 2>/dev/null || echo "Unable to list service accounts"
    
    echo ""
}

# Function to get user input with validation
get_user_input() {
    local prompt="$1"
    local var_name="$2"
    local validation_func="$3"
    
    while true; do
        echo -e "${YELLOW}$prompt${NC}"
        read -r input
        
        if [ -n "$validation_func" ]; then
            if $validation_func "$input"; then
                eval "$var_name='$input'"
                break
            else
                echo -e "${RED}❌ Invalid input. Please try again.${NC}"
            fi
        else
            if [ -n "$input" ]; then
                eval "$var_name='$input'"
                break
            else
                echo -e "${RED}❌ Input cannot be empty. Please try again.${NC}"
            fi
        fi
    done
}

# Validation functions
validate_project_id() {
    local project_id="$1"
    # Check if project exists and is accessible
    gcloud projects describe "$project_id" >/dev/null 2>&1
}

validate_cluster() {
    local cluster="$1"
    local zone="$2"
    # Check if cluster exists in the specified zone
    gcloud container clusters describe "$cluster" --zone="$zone" >/dev/null 2>&1
}

validate_namespace() {
    local namespace="$1"
    # Check if namespace exists or can be created
    kubectl get namespace "$namespace" >/dev/null 2>&1 || kubectl create namespace "$namespace" >/dev/null 2>&1
}

# Check prerequisites
echo -e "${YELLOW}📋 Checking prerequisites...${NC}"

if ! command_exists gcloud; then
    echo -e "${RED}❌ gcloud CLI not found. Please install it first:${NC}"
    echo "   https://cloud.google.com/sdk/docs/install"
    exit 1
fi

if ! command_exists kubectl; then
    echo -e "${RED}❌ kubectl not found. Please install it first:${NC}"
    echo "   https://kubernetes.io/docs/tasks/tools/"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites check passed${NC}"

# Display current project information
display_project_info

# Get project details
echo -e "${BLUE}🔧 Project Configuration${NC}"
echo "========================"

get_user_input "📝 Enter your GCP Project ID:" "PROJECT_ID" "validate_project_id"

# Set project
echo -e "${YELLOW}🔧 Setting GCP project to: $PROJECT_ID${NC}"
gcloud config set project "$PROJECT_ID"

# Enable required APIs
echo -e "${YELLOW}🔌 Enabling required APIs...${NC}"
gcloud services enable generativelanguage.googleapis.com
gcloud services enable aiplatform.googleapis.com
gcloud services enable container.googleapis.com

echo -e "${GREEN}✅ APIs enabled${NC}"

# Service account configuration
echo -e "${BLUE}👤 Service Account Configuration${NC}"
echo "==============================="

# Ask if user wants to use existing service account
echo -e "${YELLOW}Do you want to use an existing service account? (y/n):${NC}"
read -r use_existing

if [[ "$use_existing" =~ ^[Yy]$ ]]; then
    USE_EXISTING_SA=true
    get_user_input "📝 Enter the email of your existing service account:" "EXISTING_SA_EMAIL"
    SERVICE_ACCOUNT_NAME=$(echo "$EXISTING_SA_EMAIL" | cut -d'@' -f1)
    echo -e "${GREEN}✅ Using existing service account: $EXISTING_SA_EMAIL${NC}"
else
    # Create new service account
    echo -e "${YELLOW}👤 Creating new service account...${NC}"
    gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" \
        --display-name="Bank Asset Agent Service Account" \
        --description="Service account for Bank Asset Agent AI operations" \
        --quiet || echo -e "${YELLOW}⚠️  Service account may already exist${NC}"
    EXISTING_SA_EMAIL="$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com"
fi

# Grant permissions
echo -e "${YELLOW}🔐 Granting permissions...${NC}"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$EXISTING_SA_EMAIL" \
    --role="roles/aiplatform.user" \
    --quiet

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$EXISTING_SA_EMAIL" \
    --role="roles/aiplatform.serviceAgent" \
    --quiet

echo -e "${GREEN}✅ Permissions granted${NC}"

# Create and download service account key
echo -e "${YELLOW}🔑 Creating service account key...${NC}"
gcloud iam service-accounts keys create "$KEY_FILE" \
    --iam-account="$EXISTING_SA_EMAIL"

echo -e "${GREEN}✅ Service account key created: $KEY_FILE${NC}"

# Cluster configuration
echo -e "${BLUE}☸️  Kubernetes Cluster Configuration${NC}"
echo "=================================="

get_user_input "📝 Enter your GKE cluster name:" "CLUSTER_NAME"

# Ask for zone or region
echo -e "${YELLOW}Is your cluster in a zone (z) or region (r)? (z/r):${NC}"
read -r location_type

if [[ "$location_type" =~ ^[Zz]$ ]]; then
    get_user_input "📝 Enter your GKE cluster zone (e.g., us-central1-a):" "ZONE"
    LOCATION="$ZONE"
else
    get_user_input "📝 Enter your GKE cluster region (e.g., us-central1):" "REGION"
    LOCATION="$REGION"
fi

# Get cluster credentials
echo -e "${YELLOW}🔗 Getting cluster credentials...${NC}"
if [[ "$location_type" =~ ^[Zz]$ ]]; then
    gcloud container clusters get-credentials "$CLUSTER_NAME" --zone="$ZONE"
else
    gcloud container clusters get-credentials "$CLUSTER_NAME" --region="$REGION"
fi

# Namespace configuration
echo -e "${BLUE}📁 Namespace Configuration${NC}"
echo "========================"

get_user_input "📝 Enter the Kubernetes namespace (default: default):" "NAMESPACE"
if [ -z "$NAMESPACE" ]; then
    NAMESPACE="default"
fi

# Create namespace if it doesn't exist
echo -e "${YELLOW}📁 Ensuring namespace exists...${NC}"
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

# Create Kubernetes secrets
echo -e "${YELLOW}🔐 Creating Kubernetes secrets...${NC}"

# Create secret for service account credentials
kubectl create secret generic bank-asset-agent-credentials \
    --from-file=credentials.json="$KEY_FILE" \
    --namespace="$NAMESPACE" \
    --dry-run=client -o yaml | kubectl apply -f -

# Create secret for Gemini API key
echo -e "${YELLOW}🔑 Enter your Gemini API key:${NC}"
read -s GEMINI_API_KEY
echo

kubectl create secret generic gemini-api-key \
    --from-literal=api-key="$GEMINI_API_KEY" \
    --namespace="$NAMESPACE" \
    --dry-run=client -o yaml | kubectl apply -f -

echo -e "${GREEN}✅ Kubernetes secrets created${NC}"

# Verify secrets
echo -e "${YELLOW}🔍 Verifying secrets...${NC}"
kubectl get secrets -n "$NAMESPACE" | grep -E "(bank-asset-agent-credentials|gemini-api-key)"

# Verify cluster connectivity
echo -e "${YELLOW}🔍 Verifying cluster connectivity...${NC}"
kubectl get nodes --no-headers | wc -l | xargs -I {} echo "✅ Connected to cluster with {} nodes"

# Clean up local key file
echo -e "${YELLOW}🧹 Cleaning up local key file...${NC}"
rm -f "$KEY_FILE"

# Display configuration summary
echo -e "${BLUE}📊 Configuration Summary${NC}"
echo "======================="
echo -e "${YELLOW}Project ID:${NC} $PROJECT_ID"
echo -e "${YELLOW}Service Account:${NC} $EXISTING_SA_EMAIL"
echo -e "${YELLOW}Cluster:${NC} $CLUSTER_NAME"
echo -e "${YELLOW}Location:${NC} $LOCATION"
echo -e "${YELLOW}Namespace:${NC} $NAMESPACE"
echo ""

echo -e "${GREEN}✅ Setup completed successfully!${NC}"
echo ""
echo -e "${BLUE}📋 Next steps:${NC}"
echo "1. Deploy the bank-asset-agent:"
echo "   kubectl apply -f k8s/base/ -n $NAMESPACE"
echo ""
echo "2. Check deployment status:"
echo "   kubectl get pods -l app=bank-asset-agent -n $NAMESPACE"
echo ""
echo "3. View logs:"
echo "   kubectl logs -l app=bank-asset-agent -n $NAMESPACE -f"
echo ""
echo "4. Test AI functionality:"
echo "   kubectl exec -it deployment/bank-asset-agent -n $NAMESPACE -- python -m pytest tests/test_ai_integration.py"
echo ""
echo -e "${GREEN}🎉 Bank Asset Agent is ready for AI operations!${NC}"
echo ""
echo -e "${CYAN}💡 Tip: Run 'kubectl get all -n $NAMESPACE' to see all resources${NC}"
