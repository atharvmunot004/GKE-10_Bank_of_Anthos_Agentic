# Deploy Bank of Anthos Infrastructure using Google Cloud Console

This guide shows you how to deploy your infrastructure using the Google Cloud Console web interface.

## Prerequisites

1. **Google Cloud Account** with billing enabled
2. **Project ID**: `ffd-gke10`
3. **Region**: `us-central1`

## Step 1: Enable Required APIs

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project: `ffd-gke10`
3. Go to **APIs & Services** → **Library**
4. Enable these APIs:
   - **Cloud Build API**
   - **Cloud Deploy API**
   - **Kubernetes Engine API**
   - **Artifact Registry API**
   - **Cloud Storage API**
   - **Compute Engine API**
   - **GKE Hub API**
   - **Anthos API**

## Step 2: Create Artifact Registry Repository

1. Go to **Artifact Registry** → **Repositories**
2. Click **Create Repository**
3. **Name**: `bank-of-anthos`
4. **Format**: Docker
5. **Location**: `us-central1`
6. **Description**: `Bank of Anthos container images`
7. Click **Create**

## Step 3: Create GKE Autopilot Clusters

### Development Cluster
1. Go to **Kubernetes Engine** → **Clusters**
2. Click **Create Cluster**
3. **Cluster mode**: Autopilot
4. **Name**: `development`
5. **Location**: Regional
6. **Region**: `us-central1`
7. Click **Create**

### Staging Cluster
1. Repeat the above steps
2. **Name**: `staging`
3. All other settings the same

### Production Cluster
1. Repeat the above steps
2. **Name**: `production`
3. All other settings the same

## Step 4: Create Storage Buckets

1. Go to **Cloud Storage** → **Buckets**
2. Create these buckets:
   - `build-cache-main-ffd-gke10`
   - `build-cache-pr-ffd-gke10`
   - `delivery-artifacts-staging-ffd-gke10`
   - `delivery-artifacts-production-ffd-gke10`

## Step 5: Create Service Accounts

### Cloud Build Service Account
1. Go to **IAM & Admin** → **Service Accounts**
2. Click **Create Service Account**
3. **Name**: `cloud-build-main`
4. **Description**: `Service account for main branch CI/CD`
5. Click **Create and Continue**
6. Grant these roles:
   - **Cloud Build Editor**
   - **Kubernetes Engine Developer**
   - **Storage Admin**
   - **Artifact Registry Administrator**
7. Click **Done**

### Cloud Deploy Service Account
1. Create another service account
2. **Name**: `cloud-deploy`
3. **Description**: `Service account for Cloud Deploy`
4. Grant these roles:
   - **Cloud Deploy Developer**
   - **Kubernetes Engine Developer**
   - **Storage Admin**

## Step 6: Create Cloud Build Triggers

### Main Branch Trigger
1. Go to **Cloud Build** → **Triggers**
2. Click **Create Trigger**
3. **Name**: `main-branch-cicd`
4. **Event**: Push to a branch
5. **Source**: Connect your GitHub repository
   - **Repository**: `atharvmunot004/GKE-10_Bank_of_Anthos_Agentic`
   - **Branch**: `^main$`
6. **Configuration**: Cloud Build configuration file
7. **Location**: `.github/cloudbuild/ci-main.yaml`
8. **Service account**: `cloud-build-main@ffd-gke10.iam.gserviceaccount.com`
9. Click **Create**

### PR Trigger
1. Create another trigger
2. **Name**: `pull-request-ci`
3. **Event**: Pull request
4. **Source**: Same repository
5. **Configuration**: `.github/cloudbuild/ci-pr.yaml`
6. **Service account**: Same as above
7. Click **Create**

## Step 7: Create Cloud Deploy Targets

### Register Cluster Memberships
1. Go to **GKE Hub** → **Memberships**
2. Click **Register Existing Cluster**
3. **Cluster**: `development` (from us-central1)
4. **Name**: `development`
5. Click **Register**
6. Repeat for `staging` and `production` clusters

### Create Deployment Targets
1. Go to **Cloud Deploy** → **Targets**
2. Click **Create Target**
3. **Name**: `staging`
4. **Target type**: GKE
5. **Membership**: `staging`
6. **Execution config**:
   - **Storage location**: `gs://delivery-artifacts-staging-ffd-gke10`
   - **Service account**: `cloud-deploy@ffd-gke10.iam.gserviceaccount.com`
7. Click **Create**
8. Repeat for `production` target

## Step 8: Create Delivery Pipeline

1. Go to **Cloud Deploy** → **Delivery Pipelines**
2. Click **Create Delivery Pipeline**
3. **Name**: `main-branch-pipeline`
4. **Targets**: Add `staging` and `production`
5. **Strategy**: Standard
6. Click **Create**

## Step 9: Set Up GitHub Secrets

1. Go to your GitHub repository
2. **Settings** → **Secrets and variables** → **Actions**
3. Add these secrets:
   - **GCP_PROJECT_ID**: `ffd-gke10`
   - **GCP_SA_KEY**: [Service account key JSON]

### Create Service Account Key
1. Go to **IAM & Admin** → **Service Accounts**
2. Click on `cloud-build-main@ffd-gke10.iam.gserviceaccount.com`
3. Go to **Keys** tab
4. Click **Add Key** → **Create new key**
5. **Type**: JSON
6. Download the key file
7. Copy the entire JSON content to GitHub secret `GCP_SA_KEY`

## Step 10: Test Deployment

1. Make a small change to any file in your repository
2. Commit and push to `main` branch
3. Go to **Cloud Build** → **History** to see the build
4. Go to **Cloud Deploy** → **Releases** to see the deployment
5. Check your GKE clusters for deployed services

## Verification

After completing all steps, you should have:

✅ **3 GKE Autopilot clusters** (development, staging, production)  
✅ **1 Artifact Registry repository**  
✅ **4 Cloud Storage buckets**  
✅ **2 Service accounts** with proper permissions  
✅ **2 Cloud Build triggers**  
✅ **3 Cloud Deploy targets**  
✅ **1 Delivery pipeline**  
✅ **GitHub secrets** configured  

## Troubleshooting

### Common Issues

1. **Permission denied**: Check service account roles
2. **API not enabled**: Enable required APIs
3. **Cluster not found**: Ensure clusters are created and registered
4. **Build fails**: Check build logs in Cloud Build console

### Useful Commands

```bash
# Check cluster status
gcloud container clusters list

# Check service accounts
gcloud iam service-accounts list

# Check build triggers
gcloud builds triggers list

# View build logs
gcloud builds log BUILD_ID
```

## Next Steps

Once your infrastructure is deployed:

1. **Push code to main branch** to trigger first deployment
2. **Monitor deployment** in Cloud Build and Cloud Deploy consoles
3. **Verify services** are running in GKE clusters
4. **Test your application** in staging environment
5. **Deploy to production** after testing

Your CI/CD pipeline will now automatically build and deploy all 22 services when you push to the main branch!