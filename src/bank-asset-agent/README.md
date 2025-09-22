# Bank Asset Agent - AI-Powered Investment Management

The Bank Asset Agent is an AI-powered service that manages the bank's asset portfolio and provides intelligent investment recommendations. It analyzes market data using Google's Gemini AI, manages assets in the assets-db, and provides investment intelligence to other services when called. The agent does NOT process user queues directly - it focuses purely on asset management and AI-powered investment decisions.

## 🤖 AI Capabilities

### Core AI Features
- **AI Market Analysis**: Advanced market trend analysis using Google Gemini AI
- **Intelligent Investment Decisions**: AI-powered investment approval/rejection with detailed reasoning
- **Portfolio Optimization**: AI-driven portfolio rebalancing and allocation recommendations
- **Risk Assessment**: AI risk analysis with stress testing and mitigation strategies
- **Price Prediction**: ML-based asset price prediction with confidence metrics
- **Sentiment Analysis**: News and social media sentiment analysis for market insights

### AI Tools
- **AIMarketAnalyzer**: AI-powered market analysis and trend prediction
- **AIDecisionMaker**: Intelligent investment decision making and risk assessment
- **AIPortfolioManager**: Dynamic portfolio optimization and management
- **MarketAnalyzer**: Hybrid market analysis with AI enhancement and fallback

## 🏗️ Architecture

### Service Dependencies
1. **market-reader-svc**: Real-time market data and pricing information
2. **rule-checker-svc**: Business rule validation and compliance checking
3. **execute-order-svc**: Investment order execution and management
4. **assets-db**: Asset information storage and retrieval
5. **user-request-queue-svc**: Investment and withdrawal request processing

### AI Integration
- **Google Gemini API**: Primary AI engine for all intelligent operations
- **Fallback Mechanisms**: Rule-based logic when AI is unavailable
- **Caching**: Intelligent response caching to optimize performance
- **Error Handling**: Robust error handling with graceful degradation

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Google Cloud Account with Gemini API access
- PostgreSQL database access

### Installation

1. **Clone and navigate to the service**:
   ```bash
   cd src/bank-asset-agent
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   export GEMINI_API_KEY=your_gemini_api_key
   export ASSETS_DB_URI=postgresql://user:password@localhost:5432/assets_db
   export QUEUE_DB_URI=postgresql://user:password@localhost:5432/queue_db
   ```

4. **Start the service**:
   ```bash
   python server.py
   ```

### AI Setup
For detailed AI setup instructions, see:
- **Local Development**: [SETUP_AI.md](SETUP_AI.md)
- **GCP Deployment**: [GCP_AI_SETUP.md](GCP_AI_SETUP.md)

### Quick GCP Setup
```bash
# 1. First, check your GCP project information
./show-gcp-info.sh

# 2. Run automated GCP setup
./setup-gcp-ai.sh

# 3. Or follow manual steps in GCP_AI_SETUP.md
```

## 📡 API Endpoints

### Health Check
```http
GET /health
```

### Market Analysis
```http
POST /api/v1/market/analyze
Content-Type: application/json

{
  "symbols": ["AAPL", "GOOGL", "MSFT"],
  "time_range": "1d"
}
```

### Price Prediction
```http
POST /api/v1/market/predict
Content-Type: application/json

{
  "historical_data": [
    {"symbol": "AAPL", "price": 150.25, "timestamp": "2024-09-22T10:30:00Z"}
  ],
  "horizon": "1h"
}
```

### Investment Decision
```http
POST /api/v1/investment/decide
Content-Type: application/json

{
  "investment_request": {
    "account_number": "12345",
    "asset_symbol": "AAPL",
    "amount": 1000,
    "investment_type": "buy",
    "user_tier": 2
  },
  "market_data": {
    "AAPL": {"price": 150.25, "volatility": 0.15, "trend": "bullish"}
  },
  "user_profile": {
    "risk_tolerance": "medium",
    "investment_goals": ["growth"],
    "time_horizon": "5_years"
  },
  "risk_rules": {
    "max_investment_amount": 10000,
    "min_user_tier": 1
  }
}
```

### Portfolio Optimization
```http
POST /api/v1/portfolio/optimize
Content-Type: application/json

{
  "current_portfolio": {
    "assets": [
      {"symbol": "AAPL", "weight": 0.4},
      {"symbol": "GOOGL", "weight": 0.3},
      {"symbol": "BOND", "weight": 0.3}
    ],
    "total_value": 100000
  },
  "market_conditions": {
    "volatility": 0.15,
    "trend": "bullish"
  },
  "user_goals": {
    "goals": ["growth", "income"],
    "time_horizon": "5_years"
  },
  "risk_tolerance": "medium"
}
```

### Asset Management
```http
GET /api/v1/assets?tier=1
```

## 🧪 Testing

### Unit Tests
```bash
python -m pytest tests/test_agents.py -v
```

### AI Integration Tests
```bash
python -m pytest tests/test_ai_integration.py -v
```

### Prompt Testing
```bash
python -m pytest tests/test_prompt_testing.py -v
```

### All Tests
```bash
python -m pytest tests/ -v
```

## ⚙️ Configuration

### Environment Variables

#### AI Configuration
- `GEMINI_API_KEY`: Google Gemini AI API key
- `AI_ENABLED`: Enable AI features (default: true)
- `AI_CONFIDENCE_THRESHOLD`: Minimum confidence for AI decisions (default: 0.7)
- `AI_FALLBACK_ENABLED`: Enable fallback to rule-based logic (default: true)

#### Database Configuration
- `ASSETS_DB_URI`: Database connection URI for assets-db
- `QUEUE_DB_URI`: Database connection URI for queue-db

#### Service URLs
- `MARKET_READER_URL`: URL for market-reader-svc
- `RULE_CHECKER_URL`: URL for rule-checker-svc
- `EXECUTE_ORDER_URL`: URL for execute-order-svc
- `QUEUE_SVC_URL`: URL for user-request-queue-svc

#### Application Configuration
- `PORT`: Service port (default: 8080)
- `VERSION`: Service version (default: dev)
- `DEBUG`: Enable debug mode (default: false)

## 📁 Directory Structure

```
src/bank-asset-agent/
├── ai/                          # AI integration modules
│   └── gemini_client.py         # Google Gemini AI client
├── api/                         # API layer
│   ├── grpc_service.py          # gRPC service implementation
│   ├── handlers.py              # Request handlers
│   └── models.py                # Data models
├── tools/                       # AI-powered tools
│   ├── ai_market_analyzer.py    # AI market analysis
│   ├── ai_decision_maker.py     # AI decision making
│   ├── ai_portfolio_manager.py  # AI portfolio management
│   └── market_analyzer.py       # Enhanced market analyzer
├── utils/                       # Utility modules
│   ├── http_client.py           # HTTP client utilities
│   └── db_client.py             # Database client utilities
├── tests/                       # Test suite
│   ├── test_agents.py           # Unit tests
│   ├── test_ai_integration.py   # AI integration tests
│   ├── test_prompt_testing.py   # Prompt testing framework
│   └── test_integration.py      # Integration tests
├── k8s/                         # Kubernetes manifests
├── server.py                    # Main server application
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Container definition
├── README.md                    # This file
└── SETUP_AI.md                  # AI setup guide
```

## 🔧 Development

### Adding New AI Capabilities

1. **Create AI Tool**: Add new AI-powered tools in `tools/`
2. **Update API**: Add corresponding API endpoints in `server.py`
3. **Add Tests**: Create comprehensive tests in `tests/`
4. **Update Documentation**: Update README and llm.txt files

### AI Model Integration

The service uses Google's Gemini AI through the `GeminiAIClient` class. To integrate other AI models:

1. Create a new client class in `ai/`
2. Implement the same interface as `GeminiAIClient`
3. Update the tool classes to use the new client
4. Add configuration options for model selection

## 🚨 Troubleshooting

### Common Issues

1. **AI Service Unavailable**: Check API key and network connectivity
2. **Database Connection Failed**: Verify database URIs and credentials
3. **Import Errors**: Ensure all dependencies are installed
4. **API Rate Limits**: Implement exponential backoff or upgrade quota

### Debug Mode

Enable debug mode for detailed logging:
```bash
export DEBUG=true
python server.py
```

### Health Check

Verify service health:
```bash
curl http://localhost:8080/health
```

## 📊 Monitoring

### Key Metrics
- AI API response times
- AI decision accuracy
- Fallback usage frequency
- Error rates by component
- Cache hit rates

### Logging
- All AI decisions are logged with timestamps
- Error logs include stack traces and context
- Performance metrics are tracked automatically

## 🔒 Security

- API keys are never logged or exposed
- Input validation on all endpoints
- Rate limiting for production use
- Audit logging for compliance
- Fallback mechanisms for reliability

## 📈 Performance

- AI responses are cached to reduce API calls
- Connection pooling for external services
- Async processing where applicable
- Optimized database queries

## 🚀 GCP Deployment

### Prerequisites
- GCP project with billing enabled
- GKE cluster running
- Docker and kubectl installed
- Gemini API key

### Quick Deployment
```bash
# 1. Check your GCP setup
./show-gcp-info.sh

# 2. Run the AI setup script
./setup-gcp-ai.sh

# 3. Build and push Docker image
docker build -t gcr.io/YOUR_PROJECT_ID/bank-asset-agent:latest .
docker push gcr.io/YOUR_PROJECT_ID/bank-asset-agent:latest

# 4. Update image in Kubernetes config
# Edit k8s/base/bank-asset-agent.yaml and change:
# image: bank-asset-agent
# to:
# image: gcr.io/YOUR_PROJECT_ID/bank-asset-agent:latest

# 5. Deploy to Kubernetes
kubectl apply -f k8s/base/ -n YOUR_NAMESPACE

# 6. Verify deployment
kubectl get pods -l app=bank-asset-agent -n YOUR_NAMESPACE
kubectl logs -l app=bank-asset-agent -n YOUR_NAMESPACE -f
```

### Production Deployment
```bash
# Use Skaffold for development
skaffold dev --module bank-asset-agent

# Or deploy to production
skaffold run --profile production
```

### Verification
```bash
# Test AI functionality
kubectl exec -it deployment/bank-asset-agent -n YOUR_NAMESPACE -- python -m pytest tests/test_ai_integration.py

# Check health endpoint
kubectl port-forward svc/bank-asset-agent 8080:8080 -n YOUR_NAMESPACE
curl http://localhost:8080/health
```

## 🤝 Contributing

1. Follow the existing code structure
2. Add comprehensive tests for new features
3. Update documentation for any changes
4. Ensure AI fallback mechanisms work
5. Test with both AI enabled and disabled

## 📄 License

Copyright 2024 Google LLC. Licensed under the Apache License, Version 2.0.