# AI Setup Guide for Bank Asset Agent

This guide explains how to set up and configure the AI capabilities for the Bank Asset Agent using Google's Gemini API.

## Prerequisites

1. **Google Cloud Account**: You need a Google Cloud account with billing enabled
2. **Python 3.11+**: The agent requires Python 3.11 or higher
3. **Required Dependencies**: Install the requirements.txt dependencies

## Gemini API Setup

### Step 1: Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note your project ID for later use

### Step 2: Enable the Gemini API

1. In the Google Cloud Console, go to "APIs & Services" > "Library"
2. Search for "Generative AI API" or "Vertex AI API"
3. Click on "Generative AI API" and enable it
4. Also enable "Vertex AI API" for advanced features

### Step 3: Create API Credentials

#### Option A: Using API Key (Recommended for Development)

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "API Key"
3. Copy the generated API key
4. (Optional) Restrict the API key to specific APIs and IP addresses for security

#### Option B: Using Service Account (Recommended for Production)

1. Go to "IAM & Admin" > "Service Accounts"
2. Click "Create Service Account"
3. Give it a name like "bank-asset-agent-ai"
4. Grant the following roles:
   - `Vertex AI User`
   - `AI Platform Developer`
5. Create and download the JSON key file
6. Set the environment variable: `GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json`

### Step 4: Configure Environment Variables

Create a `.env` file in the bank-asset-agent directory:

```bash
# Gemini AI Configuration
GEMINI_API_KEY=your_api_key_here
AI_ENABLED=true
AI_CONFIDENCE_THRESHOLD=0.7
AI_FALLBACK_ENABLED=true

# Database Configuration
ASSETS_DB_URI=postgresql://user:password@localhost:5432/assets_db
QUEUE_DB_URI=postgresql://user:password@localhost:5432/queue_db

# Service URLs
MARKET_READER_URL=http://market-reader-svc:8080
RULE_CHECKER_URL=http://rule-checker-svc:8080
EXECUTE_ORDER_URL=http://execute-order-svc:8080
QUEUE_SVC_URL=http://user-request-queue-svc:8080

# Application Configuration
PORT=8080
VERSION=dev
DEBUG=false
```

## Testing AI Capabilities

### 1. Unit Tests

Run the AI-specific unit tests:

```bash
cd src/bank-asset-agent
python -m pytest tests/test_agents.py::TestAIMarketAnalyzer -v
python -m pytest tests/test_agents.py::TestAIDecisionMaker -v
python -m pytest tests/test_agents.py::TestAIPortfolioManager -v
python -m pytest tests/test_agents.py::TestGeminiAIClient -v
```

### 2. Integration Tests

Run the AI integration tests:

```bash
python -m pytest tests/test_ai_integration.py -v
```

### 3. Prompt Testing

Run the prompt testing framework:

```bash
python -m pytest tests/test_prompt_testing.py -v
```

### 4. Manual Testing

Start the server and test the AI endpoints:

```bash
# Start the server
python server.py

# Test market analysis
curl -X POST http://localhost:8080/api/v1/market/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["AAPL", "GOOGL", "MSFT"],
    "time_range": "1d"
  }'

# Test investment decision
curl -X POST http://localhost:8080/api/v1/investment/decide \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
```

## AI Capabilities Overview

### 1. Market Analysis (`AIMarketAnalyzer`)
- **Trend Analysis**: AI-powered market trend analysis with confidence scoring
- **Price Prediction**: ML-based asset price prediction with reasoning
- **Sentiment Analysis**: News and social media sentiment analysis
- **Risk Assessment**: AI portfolio risk analysis with stress testing

### 2. Investment Decision Making (`AIDecisionMaker`)
- **Investment Decisions**: AI investment approval/rejection with detailed reasoning
- **Risk Assessment**: AI risk analysis with mitigation strategies
- **Compliance Validation**: AI-powered compliance checking
- **Alternative Strategies**: AI alternative investment suggestions

### 3. Portfolio Management (`AIPortfolioManager`)
- **Portfolio Optimization**: AI portfolio rebalancing recommendations
- **Diversification Analysis**: AI diversification analysis and scoring
- **Performance Assessment**: AI performance analysis and recommendations
- **Asset Allocation**: AI asset allocation recommendations

## Configuration Options

### AI Settings

- `AI_ENABLED`: Enable/disable AI features (default: true)
- `AI_CONFIDENCE_THRESHOLD`: Minimum confidence for AI decisions (default: 0.7)
- `AI_FALLBACK_ENABLED`: Enable fallback to rule-based logic (default: true)

### Gemini API Settings

- `GEMINI_API_KEY`: Your Gemini API key
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account key file (alternative to API key)

## Troubleshooting

### Common Issues

1. **API Key Not Found**
   ```
   ValueError: Gemini API key not provided
   ```
   Solution: Set the `GEMINI_API_KEY` environment variable

2. **API Rate Limit Exceeded**
   ```
   Exception: API rate limit exceeded
   ```
   Solution: Implement exponential backoff or upgrade your API quota

3. **AI Service Unavailable**
   ```
   Exception: AI service unavailable
   ```
   Solution: Check your internet connection and API key validity

4. **Import Errors**
   ```
   ModuleNotFoundError: No module named 'google.generativeai'
   ```
   Solution: Install requirements: `pip install -r requirements.txt`

### Debug Mode

Enable debug mode for detailed logging:

```bash
export DEBUG=true
python server.py
```

### Health Check

Check if AI capabilities are working:

```bash
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-09-22T10:30:00Z",
  "ai_enabled": true,
  "version": "dev"
}
```

## Security Considerations

1. **API Key Security**: Never commit API keys to version control
2. **Rate Limiting**: Implement rate limiting for production use
3. **Input Validation**: Validate all inputs to AI endpoints
4. **Audit Logging**: Log all AI decisions for compliance
5. **Fallback Mechanisms**: Always have fallback logic when AI fails

## Performance Optimization

1. **Caching**: AI responses are cached to reduce API calls
2. **Batch Processing**: Process multiple requests together when possible
3. **Connection Pooling**: Reuse HTTP connections for external services
4. **Async Processing**: Use async/await for non-blocking operations

## Monitoring and Metrics

Monitor the following metrics:
- AI API response times
- AI decision accuracy
- Fallback usage frequency
- Error rates by AI component
- Cache hit rates

## Support

For issues related to:
- **Gemini API**: Check [Google AI documentation](https://ai.google.dev/docs)
- **Bank Asset Agent**: Check the project documentation
- **Integration Issues**: Review the test cases and examples
