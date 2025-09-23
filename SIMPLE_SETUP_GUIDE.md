# Simple Bank of Anthos CI/CD Setup Guide

This guide shows you how to set up automated CI/CD for your Bank of Anthos project using your existing GKE cluster.

## Current Status ✅

- **Project ID**: `ffd-gke10`
- **Cluster**: `bank-of-anthos` (existing)
- **Region**: `us-central1`
- **Artifact Registry**: `bank-of-anthos` (created)

## Quick Setup (5 minutes)

### Step 1: Create Service Account Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select project: `ffd-gke10`
3. Go to **IAM & Admin** → **Service Accounts**
4. Click **Create Service Account**
5. **Name**: `github-actions-simple`
6. **Description**: `Service account for GitHub Actions`
7. Grant these roles:
   - **Cloud Build Editor**
   - **Kubernetes Engine Developer**
   - **Artifact Registry Administrator**
   - **Storage Admin**
8. Click **Keys** tab → **Add Key** → **Create new key** → **JSON**
9. Download the key file

### Step 2: Set Up GitHub Secrets

1. Go to your GitHub repository: `atharvmunot004/GKE-10_Bank_of_Anthos_Agentic`
2. **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. **Name**: `GCP_SA_KEY`
5. **Value**: Paste the entire JSON content from the downloaded key file
6. Click **Add secret**

### Step 3: Test the Pipeline

1. Make a small change to any file (e.g., add a comment)
2. Commit and push to `main` branch:
   ```bash
   git add .
   git commit -m "Test CI/CD pipeline"
   git push origin main
   ```

3. Go to **Actions** tab in your GitHub repository
4. Watch the workflow run

## What the Pipeline Does

### Automatic Process:
1. **Triggers**: When you push to `main` branch
2. **Builds**: Container images for your services
3. **Pushes**: Images to Artifact Registry
4. **Deploys**: Services to your GKE cluster
5. **Verifies**: Deployment is successful

### Services Included:
- `frontend`
- `investment-manager-svc`
- `invest-svc`
- `user-tier-agent`

## Manual Deployment (Alternative)

If you prefer manual deployment:

```bash
# Get cluster credentials
gcloud container clusters get-credentials bank-of-anthos --region=us-central1

# Build and push images manually
cd src/frontend
docker build -t us-central1-docker.pkg.dev/ffd-gke10/bank-of-anthos/frontend:latest .
docker push us-central1-docker.pkg.dev/ffd-gke10/bank-of-anthos/frontend:latest

# Deploy to cluster
kubectl apply -f kubernetes-manifests/
```

## Monitoring Your Deployment

### Check Build Status:
- **GitHub Actions**: Go to Actions tab in your repository
- **Cloud Build**: [Console](https://console.cloud.google.com/cloud-build/builds?project=ffd-gke10)

### Check Deployment Status:
```bash
# Get cluster credentials
gcloud container clusters get-credentials bank-of-anthos --region=us-central1

# Check pods
kubectl get pods

# Check services
kubectl get services

# Check deployments
kubectl get deployments
```

### View Logs:
```bash
# View pod logs
kubectl logs -l app=frontend

# View all logs
kubectl logs --all-containers=true --all-namespaces
```

## Troubleshooting

### Common Issues:

1. **Build fails**:
   - Check GitHub Actions logs
   - Verify service account has correct permissions
   - Check Dockerfile exists in service directory

2. **Deployment fails**:
   - Check cluster status: `gcloud container clusters describe bank-of-anthos --region=us-central1`
   - Verify cluster is running: `gcloud container clusters list`

3. **Authentication fails**:
   - Verify `GCP_SA_KEY` secret is set correctly
   - Check service account permissions

### Useful Commands:

```bash
# Check cluster status
gcloud container clusters list

# Get cluster details
gcloud container clusters describe bank-of-anthos --region=us-central1

# View build history
gcloud builds list --limit=10

# Check service account
gcloud iam service-accounts list
```

## Next Steps

Once your pipeline is working:

1. **Add more services**: Update the workflow to include all 22 services
2. **Add testing**: Include unit tests in the pipeline
3. **Add monitoring**: Set up monitoring and alerting
4. **Add staging**: Create separate environments for testing

## Cost Optimization

Your current setup is cost-optimized:
- **Single cluster**: Uses existing `bank-of-anthos` cluster
- **On-demand builds**: Only builds when you push code
- **Efficient images**: Uses multi-stage builds and caching

## Support

If you need help:
1. Check the GitHub Actions logs
2. Review the Google Cloud Build console
3. Verify your service account permissions
4. Check cluster status and resources

Your CI/CD pipeline is now ready! Every push to main will automatically build and deploy your services. 🚀
