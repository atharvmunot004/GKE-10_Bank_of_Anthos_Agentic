# GCP AI Setup Guide for Bank Asset Agent

This guide provides comprehensive instructions for setting up Gemini AI integration in Google Cloud Platform (GCP) for the Bank Asset Agent.

## 🎯 Overview

The Bank Asset Agent uses Google's Gemini AI for:
- Market trend analysis
- Investment decision making
- Portfolio optimization
- Risk assessment
- Prompt engineering

## 📋 Prerequisites

1. **Google Cloud Account** with billing enabled
2. **gcloud CLI** installed and configured
3. **kubectl** installed
4. **GKE Cluster** running
5. **Project ID** with appropriate permissions

## 🚀 Quick Setup (Automated)

### Option 1: Use the Setup Script

```bash
# Navigate to bank-asset-agent directory
cd src/bank-asset-agent

# Run the automated setup script
./setup-gcp-ai.sh
```

The script will:
- ✅ Check prerequisites
- ✅ Enable required APIs
- ✅ Create service account
- ✅ Grant permissions
- ✅ Create Kubernetes secrets
- ✅ Clean up temporary files

## 🔧 Manual Setup

### Step 1: Enable Required APIs

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable Generative AI API
gcloud services enable generativelanguage.googleapis.com

# Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com

# Enable Container API (for GKE)
gcloud services enable container.googleapis.com

# Verify APIs are enabled
gcloud services list --enabled --filter="name:generativelanguage OR name:aiplatform"
```

### Step 2: Create Service Account

```bash
# Create service account
gcloud iam service-accounts create bank-asset-agent-sa \
  --display-name="Bank Asset Agent Service Account" \
  --description="Service account for Bank Asset Agent AI operations"

# Grant AI Platform User role
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:bank-asset-agent-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# Grant Vertex AI Service Agent role
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:bank-asset-agent-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.serviceAgent"
```

### Step 3: Create Service Account Key

```bash
# Create and download service account key
gcloud iam service-accounts keys create bank-asset-agent-key.json \
  --iam-account=bank-asset-agent-sa@$PROJECT_ID.iam.gserviceaccount.com
```

### Step 4: Configure Kubernetes

```bash
# Get cluster credentials
gcloud container clusters get-credentials YOUR_CLUSTER_NAME --zone=YOUR_ZONE

# Create secret for service account credentials
kubectl create secret generic bank-asset-agent-credentials \
  --from-file=credentials.json=bank-asset-agent-key.json

# Create secret for Gemini API key
kubectl create secret generic gemini-api-key \
  --from-literal=api-key="YOUR_GEMINI_API_KEY"

# Clean up local key file
rm bank-asset-agent-key.json
```

## 🔐 Authentication Methods

### Method 1: Service Account (Recommended for Production)

**Advantages:**
- More secure
- Better for production
- Automatic credential rotation
- Fine-grained permissions

**Configuration:**
```yaml
env:
  - name: GOOGLE_APPLICATION_CREDENTIALS
    value: "/etc/credentials/credentials.json"
```

### Method 2: API Key (Development/Testing)

**Advantages:**
- Simpler setup
- Good for development
- Easy to test

**Configuration:**
```yaml
env:
  - name: GEMINI_API_KEY
    valueFrom:
      secretKeyRef:
        name: gemini-api-key
        key: api-key
```

## 🏗️ Kubernetes Configuration

The Bank Asset Agent Kubernetes deployment includes:

### Environment Variables
```yaml
env:
  - name: GOOGLE_APPLICATION_CREDENTIALS
    value: "/etc/credentials/credentials.json"
  - name: GEMINI_API_KEY
    valueFrom:
      secretKeyRef:
        name: gemini-api-key
        key: api-key
```

### Volume Mounts
```yaml
volumeMounts:
  - name: credentials
    mountPath: /etc/credentials
    readOnly: true
volumes:
  - name: credentials
    secret:
      secretName: bank-asset-agent-credentials
```

## 🧪 Testing AI Integration

### 1. Deploy the Agent
```bash
# Apply Kubernetes configuration
kubectl apply -f k8s/base/

# Check deployment status
kubectl get pods -l app=bank-asset-agent

# View logs
kubectl logs -l app=bank-asset-agent -f
```

### 2. Test AI Functionality
```bash
# Run AI integration tests
kubectl exec -it deployment/bank-asset-agent -- python -m pytest tests/test_ai_integration.py

# Run prompt testing
kubectl exec -it deployment/bank-asset-agent -- python -m pytest tests/test_prompt_testing.py
```

### 3. Verify AI Capabilities
```bash
# Check health endpoint
kubectl port-forward svc/bank-asset-agent 8080:8080
curl http://localhost:8080/health

# Test AI market analysis (if API endpoints are implemented)
curl -X POST http://localhost:8080/api/analyze-market \
  -H "Content-Type: application/json" \
  -d '{"market_data": {"symbol": "AAPL", "price": 150.0}}'
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Authentication Errors
```bash
# Check service account permissions
gcloud projects get-iam-policy $PROJECT_ID

# Verify service account key
gcloud auth activate-service-account --key-file=bank-asset-agent-key.json
gcloud auth list
```

#### 2. API Not Enabled
```bash
# Check enabled APIs
gcloud services list --enabled --filter="name:generativelanguage"

# Enable if needed
gcloud services enable generativelanguage.googleapis.com
```

#### 3. Kubernetes Secret Issues
```bash
# Check secrets
kubectl get secrets

# Describe secret
kubectl describe secret bank-asset-agent-credentials

# Check pod logs
kubectl logs -l app=bank-asset-agent
```

#### 4. AI Client Errors
```bash
# Check environment variables in pod
kubectl exec -it deployment/bank-asset-agent -- env | grep -E "(GEMINI|GOOGLE)"

# Test AI client directly
kubectl exec -it deployment/bank-asset-agent -- python -c "
from ai.gemini_client import GeminiAIClient
client = GeminiAIClient()
print('AI client initialized successfully')
"
```

## 📊 Monitoring and Logging

### View AI Operations
```bash
# Stream logs
kubectl logs -l app=bank-asset-agent -f | grep -i "ai\|gemini"

# Check AI-specific metrics
kubectl top pods -l app=bank-asset-agent
```

### Monitor API Usage
- Check Google Cloud Console > APIs & Services > Quotas
- Monitor Vertex AI usage in Cloud Console
- Set up billing alerts for AI API usage

## 🔒 Security Best Practices

1. **Use Service Accounts**: Prefer service accounts over API keys for production
2. **Rotate Keys**: Regularly rotate service account keys
3. **Least Privilege**: Grant only necessary permissions
4. **Secret Management**: Use Kubernetes secrets or external secret management
5. **Network Policies**: Implement network policies for AI service access
6. **Audit Logging**: Enable audit logs for AI operations

## 📈 Cost Optimization

1. **Monitor Usage**: Track AI API usage and costs
2. **Set Quotas**: Implement usage quotas
3. **Caching**: Cache AI responses when appropriate
4. **Batch Requests**: Batch AI requests when possible
5. **Model Selection**: Use appropriate Gemini models for your use case

## 🚀 Production Deployment

### 1. Pre-deployment Checklist
- [ ] Service account created with proper permissions
- [ ] APIs enabled in production project
- [ ] Kubernetes secrets configured
- [ ] Network policies applied
- [ ] Monitoring and alerting set up
- [ ] Cost controls in place

### 2. Deployment Commands
```bash
# Deploy to production
kubectl apply -f k8s/overlays/production/

# Verify deployment
kubectl get pods -l app=bank-asset-agent -n production

# Run health checks
kubectl exec -it deployment/bank-asset-agent -n production -- python -m pytest tests/test_ai_integration.py
```

## 📞 Support

For issues with:
- **GCP Setup**: Check Google Cloud documentation
- **Kubernetes**: Check GKE documentation
- **AI Integration**: Check Gemini API documentation
- **Bank Asset Agent**: Check project documentation

## 🔗 Useful Links

- [Google Cloud Console](https://console.cloud.google.com)
- [Gemini API Documentation](https://ai.google.dev/docs)
- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [GKE Documentation](https://cloud.google.com/kubernetes-engine/docs)
- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
