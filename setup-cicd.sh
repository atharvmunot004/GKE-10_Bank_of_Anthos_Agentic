#!/bin/bash

# Bank of Anthos CI/CD Setup Script
# This script sets up automated CI/CD for main branch deployments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Setting up Bank of Anthos CI/CD Pipeline${NC}"

# Check if required tools are installed
check_tool() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}❌ $1 is not installed. Please install it first.${NC}"
        exit 1
    else
        echo -e "${GREEN}✅ $1 is installed${NC}"
    fi
}

echo -e "${YELLOW}📋 Checking prerequisites...${NC}"
check_tool "gcloud"
check_tool "kubectl"
check_tool "terraform"

# Get project information
read -p "Enter your GCP Project ID: " PROJECT_ID
read -p "Enter your GitHub username: " GITHUB_USERNAME
read -p "Enter your GitHub repository name: " REPO_NAME

# Update terraform variables
echo -e "${YELLOW}📝 Updating Terraform configuration...${NC}"
sed -i "s/your-gcp-project-id/$PROJECT_ID/g" iac/tf-multienv-cicd-anthos-autopilot/terraform.tfvars
sed -i "s/your-github-username/$GITHUB_USERNAME/g" iac/tf-multienv-cicd-anthos-autopilot/terraform.tfvars
sed -i "s/GKE-10/$REPO_NAME/g" iac/tf-multienv-cicd-anthos-autopilot/terraform.tfvars

# Update GitHub Actions workflow
echo -e "${YELLOW}📝 Updating GitHub Actions workflow...${NC}"
sed -i "s/\${{ secrets.GCP_PROJECT_ID }}/$PROJECT_ID/g" .github/workflows/main-branch-deploy.yml

# Set up GCP authentication
echo -e "${YELLOW}🔐 Setting up GCP authentication...${NC}"
gcloud auth login
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${YELLOW}🔧 Enabling required GCP APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com
gcloud services enable clouddeploy.googleapis.com
gcloud services enable container.googleapis.com
gcloud services enable artifactregistry.googleapis.com

# Create Artifact Registry repository
echo -e "${YELLOW}📦 Creating Artifact Registry repository...${NC}"
gcloud artifacts repositories create bank-of-anthos \
    --repository-format=docker \
    --location=us-central1 \
    --description="Bank of Anthos container images" || echo "Repository already exists"

# Set up GitHub connection
echo -e "${YELLOW}🔗 Setting up GitHub connection...${NC}"
gcloud builds connections create github github-connection \
    --region=us-central1 \
    --authorizer-token-secret-version=projects/$PROJECT_ID/secrets/github-token/versions/latest

# Deploy infrastructure with Terraform
echo -e "${YELLOW}🏗️ Deploying infrastructure with Terraform...${NC}"
cd iac/tf-multienv-cicd-anthos-autopilot
terraform init
terraform plan
terraform apply -auto-approve

echo -e "${GREEN}✅ CI/CD setup completed!${NC}"
echo -e "${YELLOW}📋 Next steps:${NC}"
echo "1. Push your code to GitHub"
echo "2. Create a GitHub Personal Access Token"
echo "3. Add the following secrets to your GitHub repository:"
echo "   - GCP_SA_KEY: Service account key JSON"
echo "   - GCP_PROJECT_ID: $PROJECT_ID"
echo "4. Push to main branch to trigger deployment"

echo -e "${GREEN}🎉 Your CI/CD pipeline is ready!${NC}"
