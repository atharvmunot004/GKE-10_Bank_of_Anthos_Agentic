#!/bin/bash

# Bank of Anthos Infrastructure Deployment using gcloud CLI
# This script deploys all infrastructure without Terraform

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="ffd-gke10"
REGION="us-central1"
ZONE="us-central1-b"

echo -e "${GREEN}🚀 Deploying Bank of Anthos Infrastructure with gcloud CLI${NC}"

# Authenticate with Google Cloud
echo -e "${YELLOW}🔐 Authenticating with Google Cloud...${NC}"
gcloud auth login
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${YELLOW}🔧 Enabling required GCP APIs...${NC}"
gcloud services enable \
    cloudbuild.googleapis.com \
    clouddeploy.googleapis.com \
    container.googleapis.com \
    artifactregistry.googleapis.com \
    storage.googleapis.com \
    compute.googleapis.com \
    gkehub.googleapis.com \
    anthos.googleapis.com

# Create Artifact Registry repository
echo -e "${YELLOW}📦 Creating Artifact Registry repository...${NC}"
gcloud artifacts repositories create bank-of-anthos \
    --repository-format=docker \
    --location=$REGION \
    --description="Bank of Anthos container images" || echo "Repository already exists"

# Create GKE Autopilot clusters
echo -e "${YELLOW}🏗️ Creating GKE Autopilot clusters...${NC}"

# Development cluster
echo "Creating development cluster..."
gcloud container clusters create-auto development \
    --region=$REGION \
    --project=$PROJECT_ID || echo "Development cluster already exists"

# Staging cluster
echo "Creating staging cluster..."
gcloud container clusters create-auto staging \
    --region=$REGION \
    --project=$PROJECT_ID || echo "Staging cluster already exists"

# Production cluster
echo "Creating production cluster..."
gcloud container clusters create-auto production \
    --region=$REGION \
    --project=$PROJECT_ID || echo "Production cluster already exists"

# Create storage buckets for CI/CD
echo -e "${YELLOW}📁 Creating storage buckets...${NC}"

# Build cache bucket
gsutil mb gs://build-cache-main-$PROJECT_ID || echo "Build cache bucket already exists"
gsutil mb gs://build-cache-pr-$PROJECT_ID || echo "PR cache bucket already exists"

# Delivery artifacts buckets
gsutil mb gs://delivery-artifacts-staging-$PROJECT_ID || echo "Staging artifacts bucket already exists"
gsutil mb gs://delivery-artifacts-production-$PROJECT_ID || echo "Production artifacts bucket already exists"

# Create service accounts
echo -e "${YELLOW}👤 Creating service accounts...${NC}"

# Cloud Build service account
gcloud iam service-accounts create cloud-build-main \
    --display-name="Cloud Build Main" \
    --description="Service account for main branch CI/CD" || echo "Service account already exists"

# Cloud Deploy service account
gcloud iam service-accounts create cloud-deploy \
    --display-name="Cloud Deploy" \
    --description="Service account for Cloud Deploy" || echo "Service account already exists"

# Grant necessary roles to service accounts
echo -e "${YELLOW}🔑 Granting IAM roles...${NC}"

# Cloud Build roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:cloud-build-main@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/container.developer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:cloud-build-main@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:cloud-build-main@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/artifactregistry.admin"

# Cloud Deploy roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:cloud-deploy@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/clouddeploy.developer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:cloud-deploy@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/container.developer"

# Create Cloud Build triggers
echo -e "${YELLOW}⚡ Creating Cloud Build triggers...${NC}"

# Main branch trigger
gcloud builds triggers create github \
    --repo-name="GKE-10_Bank_of_Anthos_Agentic" \
    --repo-owner="atharvmunot004" \
    --branch-pattern="^main$" \
    --build-config=".github/cloudbuild/ci-main.yaml" \
    --service-account="cloud-build-main@$PROJECT_ID.iam.gserviceaccount.com" \
    --name="main-branch-cicd" || echo "Main branch trigger already exists"

# PR trigger
gcloud builds triggers create github \
    --repo-name="GKE-10_Bank_of_Anthos_Agentic" \
    --repo-owner="atharvmunot004" \
    --pull-request-pattern=".*" \
    --build-config=".github/cloudbuild/ci-pr.yaml" \
    --service-account="cloud-build-main@$PROJECT_ID.iam.gserviceaccount.com" \
    --name="pull-request-ci" || echo "PR trigger already exists"

# Create Cloud Deploy targets
echo -e "${YELLOW}🎯 Creating Cloud Deploy targets...${NC}"

# Get cluster memberships
gcloud container hub memberships register development \
    --gke-cluster=$REGION/development \
    --project=$PROJECT_ID || echo "Development membership already exists"

gcloud container hub memberships register staging \
    --gke-cluster=$REGION/staging \
    --project=$PROJECT_ID || echo "Staging membership already exists"

gcloud container hub memberships register production \
    --gke-cluster=$REGION/production \
    --project=$PROJECT_ID || echo "Production membership already exists"

# Create Cloud Deploy targets
gcloud deploy targets create staging \
    --region=$REGION \
    --cluster="projects/$PROJECT_ID/locations/$REGION/memberships/staging" \
    --execution-configs="storageLocation=gs://delivery-artifacts-staging-$PROJECT_ID,serviceAccount=cloud-deploy@$PROJECT_ID.iam.gserviceaccount.com" || echo "Staging target already exists"

gcloud deploy targets create production \
    --region=$REGION \
    --cluster="projects/$PROJECT_ID/locations/$REGION/memberships/production" \
    --execution-configs="storageLocation=gs://delivery-artifacts-production-$PROJECT_ID,serviceAccount=cloud-deploy@$PROJECT_ID.iam.gserviceaccount.com" || echo "Production target already exists"

echo -e "${GREEN}✅ Infrastructure deployment completed!${NC}"
echo -e "${YELLOW}📋 Next steps:${NC}"
echo "1. Push your code to GitHub"
echo "2. Set up GitHub secrets (see GITHUB_SECRETS_SETUP.md)"
echo "3. Push to main branch to trigger deployment"

echo -e "${GREEN}🎉 Your infrastructure is ready!${NC}"
