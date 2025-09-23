# GitHub Secrets Setup for Bank of Anthos CI/CD

This guide explains how to set up the required GitHub secrets for automated CI/CD deployment.

## Required GitHub Secrets

### 1. GCP_SA_KEY
**Purpose**: Service account key for authenticating with Google Cloud Platform

**Steps to create**:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to IAM & Admin → Service Accounts
3. Click "Create Service Account"
4. Name: `github-actions-cicd`
5. Description: `Service account for GitHub Actions CI/CD`
6. Click "Create and Continue"
7. Grant the following roles:
   - `Cloud Build Editor`
   - `Cloud Deploy Developer`
   - `Cloud Deploy Approver`
   - `Cloud Deploy Releaser`
   - `Kubernetes Engine Developer`
   - `Artifact Registry Administrator`
   - `Storage Admin`
8. Click "Done"
9. Click on the created service account
10. Go to "Keys" tab
11. Click "Add Key" → "Create new key"
12. Choose "JSON" format
13. Download the key file
14. Copy the entire JSON content

**Add to GitHub**:
- Go to your GitHub repository
- Settings → Secrets and variables → Actions
- Click "New repository secret"
- Name: `GCP_SA_KEY`
- Value: Paste the entire JSON content

### 2. GCP_PROJECT_ID
**Purpose**: Your Google Cloud Project ID

**Steps**:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Copy your Project ID from the project selector

**Add to GitHub**:
- Go to your GitHub repository
- Settings → Secrets and variables → Actions
- Click "New repository secret"
- Name: `GCP_PROJECT_ID`
- Value: Your project ID (e.g., `my-bank-of-anthos-project`)

## Optional Secrets

### 3. GITHUB_TOKEN (if needed)
**Purpose**: GitHub Personal Access Token for repository access

**Steps to create**:
1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a descriptive name
4. Select scopes:
   - `repo` (full control of private repositories)
   - `workflow` (update GitHub Action workflows)
5. Click "Generate token"
6. Copy the token

**Add to GitHub**:
- Go to your GitHub repository
- Settings → Secrets and variables → Actions
- Click "New repository secret"
- Name: `GITHUB_TOKEN`
- Value: Your personal access token

## Verification

After adding all secrets:

1. **Check secrets are added**:
   - Go to your repository Settings → Secrets and variables → Actions
   - Verify all required secrets are listed

2. **Test the pipeline**:
   - Make a small change to any file
   - Commit and push to main branch
   - Go to Actions tab to see the workflow running

3. **Monitor deployment**:
   - Check Google Cloud Build for build status
   - Check GKE clusters for deployed services
   - Verify services are running in staging and production

## Troubleshooting

### Common Issues

1. **Authentication failed**:
   - Verify `GCP_SA_KEY` is correctly formatted JSON
   - Check service account has required permissions

2. **Build failed**:
   - Check `GCP_PROJECT_ID` matches your actual project ID
   - Verify required APIs are enabled

3. **Deployment failed**:
   - Check GKE cluster credentials
   - Verify cluster names match configuration

### Debug Commands

```bash
# Check service account permissions
gcloud projects get-iam-policy YOUR_PROJECT_ID

# Verify GKE clusters
gcloud container clusters list

# Check Cloud Build triggers
gcloud builds triggers list

# View build logs
gcloud builds log BUILD_ID
```

## Security Best Practices

1. **Rotate secrets regularly**:
   - Update service account keys every 90 days
   - Regenerate GitHub tokens periodically

2. **Use least privilege**:
   - Only grant necessary permissions to service accounts
   - Use environment-specific service accounts when possible

3. **Monitor access**:
   - Enable Cloud Audit Logs
   - Review GitHub Actions logs regularly

4. **Secure storage**:
   - Never commit secrets to code
   - Use GitHub Secrets for all sensitive data

## Next Steps

After setting up secrets:

1. **Push your code** to trigger the first deployment
2. **Monitor the pipeline** in GitHub Actions
3. **Verify deployments** in GKE clusters
4. **Test your services** in staging environment
5. **Deploy to production** after testing

Your CI/CD pipeline will now automatically:
- Build container images when you push to main
- Deploy to staging environment
- Run tests on staging
- Deploy to production (with manual approval)

## Support

If you encounter issues:
1. Check GitHub Actions logs
2. Review Google Cloud Build logs
3. Verify GKE cluster status
4. Check service account permissions
