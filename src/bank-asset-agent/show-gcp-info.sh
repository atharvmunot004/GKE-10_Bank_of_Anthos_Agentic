#!/bin/bash
# Copyright 2024 Google LLC
# Bank Asset Agent - GCP Information Display Script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 GCP Project Information${NC}"
echo "=========================="
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI not found. Please install it first:${NC}"
    echo "   https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Current project
echo -e "${CYAN}📊 Current GCP Project${NC}"
echo "====================="
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "None")
echo -e "${YELLOW}Current Project:${NC} $CURRENT_PROJECT"
echo ""

# All projects
echo -e "${CYAN}📋 All Available Projects${NC}"
echo "========================="
gcloud projects list --format="table(projectId,name,projectNumber,lifecycleState)" 2>/dev/null || echo "Unable to list projects"
echo ""

# GKE clusters
echo -e "${CYAN}☸️  Available GKE Clusters${NC}"
echo "=========================="
gcloud container clusters list --format="table(name,location,status,currentMasterVersion,currentNodeVersion)" 2>/dev/null || echo "No clusters found or unable to list clusters"
echo ""

# Enabled APIs
echo -e "${CYAN}🔌 Currently Enabled APIs${NC}"
echo "=========================="
gcloud services list --enabled --format="table(name,title)" 2>/dev/null | head -15 || echo "Unable to list APIs"
echo ""

# Service accounts
echo -e "${CYAN}👤 Existing Service Accounts${NC}"
echo "============================="
gcloud iam service-accounts list --format="table(email,displayName,disabled)" 2>/dev/null || echo "Unable to list service accounts"
echo ""

# Billing information
echo -e "${CYAN}💳 Billing Information${NC}"
echo "====================="
gcloud billing accounts list --format="table(name,displayName,open)" 2>/dev/null || echo "Unable to list billing accounts"
echo ""

# Current user
echo -e "${CYAN}👤 Current User${NC}"
echo "============="
gcloud auth list --filter=status:ACTIVE --format="table(account,status)" 2>/dev/null || echo "Unable to list active accounts"
echo ""

echo -e "${GREEN}✅ Information display completed${NC}"
echo ""
echo -e "${BLUE}💡 Next steps:${NC}"
echo "1. Run the setup script: ./setup-gcp-ai.sh"
echo "2. Or follow manual setup in GCP_AI_SETUP.md"
