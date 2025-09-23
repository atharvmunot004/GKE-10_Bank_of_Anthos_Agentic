# Bank of Anthos Infrastructure Deployment using PowerShell
# This script deploys all infrastructure using gcloud CLI

param(
    [string]$ProjectId = "ffd-gke10",
    [string]$Region = "us-central1",
    [string]$Zone = "us-central1-b"
)

Write-Host "🚀 Deploying Bank of Anthos Infrastructure with PowerShell" -ForegroundColor Green

# Function to check if command exists
function Test-Command($cmdname) {
    return [bool](Get-Command -Name $cmdname -ErrorAction SilentlyContinue)
}

# Check prerequisites
if (-not (Test-Command "gcloud")) {
    Write-Host "❌ gcloud CLI not found. Please install it first." -ForegroundColor Red
    exit 1
}

Write-Host "✅ gcloud CLI found" -ForegroundColor Green

# Authenticate with Google Cloud
Write-Host "🔐 Authenticating with Google Cloud..." -ForegroundColor Yellow
gcloud auth login
gcloud config set project $ProjectId

# Enable required APIs
Write-Host "🔧 Enabling required GCP APIs..." -ForegroundColor Yellow
$apis = @(
    "cloudbuild.googleapis.com",
    "clouddeploy.googleapis.com", 
    "container.googleapis.com",
    "artifactregistry.googleapis.com",
    "storage.googleapis.com",
    "compute.googleapis.com",
    "gkehub.googleapis.com",
    "anthos.googleapis.com"
)

foreach ($api in $apis) {
    Write-Host "Enabling $api..." -ForegroundColor Cyan
    gcloud services enable $api
}

# Create Artifact Registry repository
Write-Host "📦 Creating Artifact Registry repository..." -ForegroundColor Yellow
try {
    gcloud artifacts repositories create bank-of-anthos --repository-format=docker --location=$Region --description="Bank of Anthos container images"
    Write-Host "✅ Artifact Registry repository created" -ForegroundColor Green
} catch {
    Write-Host "ℹ️ Artifact Registry repository already exists" -ForegroundColor Blue
}

# Create GKE Autopilot clusters
Write-Host "🏗️ Creating GKE Autopilot clusters..." -ForegroundColor Yellow

$clusters = @("development", "staging", "production")
foreach ($cluster in $clusters) {
    Write-Host "Creating $cluster cluster..." -ForegroundColor Cyan
    try {
        gcloud container clusters create-auto $cluster --region=$Region --project=$ProjectId
        Write-Host "✅ $cluster cluster created" -ForegroundColor Green
    } catch {
        Write-Host "ℹ️ $cluster cluster already exists" -ForegroundColor Blue
    }
}

# Create storage buckets
Write-Host "📁 Creating storage buckets..." -ForegroundColor Yellow
$buckets = @(
    "build-cache-main-$ProjectId",
    "build-cache-pr-$ProjectId", 
    "delivery-artifacts-staging-$ProjectId",
    "delivery-artifacts-production-$ProjectId"
)

foreach ($bucket in $buckets) {
    Write-Host "Creating bucket $bucket..." -ForegroundColor Cyan
    try {
        gsutil mb "gs://$bucket"
        Write-Host "✅ Bucket $bucket created" -ForegroundColor Green
    } catch {
        Write-Host "ℹ️ Bucket $bucket already exists" -ForegroundColor Blue
    }
}

# Create service accounts
Write-Host "👤 Creating service accounts..." -ForegroundColor Yellow

$serviceAccounts = @(
    @{Name="cloud-build-main"; DisplayName="Cloud Build Main"; Description="Service account for main branch CI/CD"},
    @{Name="cloud-deploy"; DisplayName="Cloud Deploy"; Description="Service account for Cloud Deploy"}
)

foreach ($sa in $serviceAccounts) {
    Write-Host "Creating service account $($sa.Name)..." -ForegroundColor Cyan
    try {
        gcloud iam service-accounts create $sa.Name --display-name=$sa.DisplayName --description=$sa.Description
        Write-Host "✅ Service account $($sa.Name) created" -ForegroundColor Green
    } catch {
        Write-Host "ℹ️ Service account $($sa.Name) already exists" -ForegroundColor Blue
    }
}

# Grant IAM roles
Write-Host "🔑 Granting IAM roles..." -ForegroundColor Yellow

$roles = @(
    @{Member="serviceAccount:cloud-build-main@$ProjectId.iam.gserviceaccount.com"; Roles=@("roles/container.developer", "roles/storage.admin", "roles/artifactregistry.admin")},
    @{Member="serviceAccount:cloud-deploy@$ProjectId.iam.gserviceaccount.com"; Roles=@("roles/clouddeploy.developer", "roles/container.developer", "roles/storage.admin")}
)

foreach ($role in $roles) {
    foreach ($roleName in $role.Roles) {
        Write-Host "Granting $roleName to $($role.Member)..." -ForegroundColor Cyan
        gcloud projects add-iam-policy-binding $ProjectId --member=$role.Member --role=$roleName
    }
}

# Create Cloud Build triggers
Write-Host "⚡ Creating Cloud Build triggers..." -ForegroundColor Yellow

try {
    gcloud builds triggers create github --repo-name="GKE-10_Bank_of_Anthos_Agentic" --repo-owner="atharvmunot004" --branch-pattern="^main$" --build-config=".github/cloudbuild/ci-main.yaml" --service-account="cloud-build-main@$ProjectId.iam.gserviceaccount.com" --name="main-branch-cicd"
    Write-Host "✅ Main branch trigger created" -ForegroundColor Green
} catch {
    Write-Host "ℹ️ Main branch trigger already exists" -ForegroundColor Blue
}

try {
    gcloud builds triggers create github --repo-name="GKE-10_Bank_of_Anthos_Agentic" --repo-owner="atharvmunot004" --pull-request-pattern=".*" --build-config=".github/cloudbuild/ci-pr.yaml" --service-account="cloud-build-main@$ProjectId.iam.gserviceaccount.com" --name="pull-request-ci"
    Write-Host "✅ PR trigger created" -ForegroundColor Green
} catch {
    Write-Host "ℹ️ PR trigger already exists" -ForegroundColor Blue
}

Write-Host "✅ Infrastructure deployment completed!" -ForegroundColor Green
Write-Host "📋 Next steps:" -ForegroundColor Yellow
Write-Host "1. Push your code to GitHub" -ForegroundColor White
Write-Host "2. Set up GitHub secrets (see GITHUB_SECRETS_SETUP.md)" -ForegroundColor White
Write-Host "3. Push to main branch to trigger deployment" -ForegroundColor White

Write-Host "🎉 Your infrastructure is ready!" -ForegroundColor Green
