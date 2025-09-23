# User Tier Agent Service

## Overview

The User Tier Agent is an AI-powered microservice that intelligently allocates investment amounts across three tiers based on user transaction history and spending patterns. It uses Google's Gemini AI to analyze user behavior and make smart allocation decisions.

## Features

- **AI-Powered Allocation**: Uses Gemini AI to analyze transaction history and determine optimal tier distribution
- **JWT Authentication**: Secure token-based authentication for all requests
- **Transaction Analysis**: Analyzes user spending patterns, frequency, and amounts
- **Three-Tier System**: Allocates investments across liquid (Tier1), moderate (Tier2), and long-term (Tier3) investments
- **Fallback Mechanism**: Default allocation when AI is unavailable
- **Comprehensive Logging**: Detailed logging for monitoring and debugging

## Architecture

### Service Type
- **Category**: AI Agent Service
- **Port**: 8080
- **Protocol**: HTTP/REST
- **Authentication**: JWT Bearer Token

### Dependencies
- **Database**: ledger-db (PostgreSQL)
- **AI Service**: Google Gemini API
- **Authentication**: JWT token validation

## API Endpoints

### Health and Status
- `GET /health` - Health check endpoint
- `GET /ready` - Readiness probe (includes database connectivity)
- `GET /api/v1/status` - Service status and configuration

### Core Functionality
- `POST /api/v1/allocate` - Main tier allocation endpoint

## Request/Response Format

### POST /api/v1/allocate

**Request:**
```json
{
  "accountid": "1234567890",
  "amount": 1000.00,
  "uuid": "unique-transaction-uuid",
  "purpose": "INVEST"
}
```

**Headers:**
```
Authorization: Bearer <jwt-token>
Content-Type: application/json
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "accountid": "1234567890",
    "amount": 1000.00,
    "uuid": "unique-transaction-uuid",
    "purpose": "INVEST",
    "tier1": 350.00,
    "tier2": 450.00,
    "tier3": 200.00,
    "allocation_percentages": {
      "tier1": 35.0,
      "tier2": 45.0,
      "tier3": 20.0
    },
    "reasoning": "AI-generated allocation based on transaction patterns",
    "timestamp": "2024-01-01T10:00:00Z"
  }
}
```

## Tier Definitions

### Tier 1 (Most Liquid)
- **Description**: Cash-like investments, money market funds, short-term bonds
- **Characteristics**: High liquidity, low risk, immediate access
- **Typical Allocation**: 20-40%

### Tier 2 (Moderately Liquid)
- **Description**: Balanced funds, ETFs, medium-term investments
- **Characteristics**: Moderate liquidity, balanced risk/return
- **Typical Allocation**: 40-60%

### Tier 3 (Least Liquid)
- **Description**: Long-term investments, growth funds, real estate
- **Characteristics**: Lower liquidity, higher potential returns
- **Typical Allocation**: 20-40%

## AI Decision Process

### Transaction Analysis
The service analyzes user transaction history to determine:

1. **Transaction Frequency**: How often the user makes transactions
2. **Amount Patterns**: Average, median, and range of transaction amounts
3. **Spending Consistency**: Whether spending is regular or variable
4. **Recent Trends**: Changes in spending behavior over time
5. **Risk Indicators**: Implied risk tolerance from transaction behavior

### Allocation Logic
Based on the analysis, the AI determines:

- **Conservative Users**: Higher Tier1 allocation for frequent small transactions
- **Balanced Users**: Even distribution across all tiers
- **Aggressive Users**: Higher Tier3 allocation for infrequent large transactions

### Fallback Mechanism
When AI is unavailable:
- **Default Allocation**: 30% Tier1, 50% Tier2, 20% Tier3
- **Reasoning**: Conservative distribution ensuring liquidity

## Environment Variables

### Required
- `LEDGER_DB_URI`: PostgreSQL connection string for ledger-db
- `JWT_SECRET_KEY`: Secret key for JWT token validation

### Optional
- `GEMINI_API_KEY`: Google Gemini API key (if not set, uses default allocation)
- `GEMINI_API_URL`: Gemini API endpoint URL
- `JWT_ALGORITHM`: JWT algorithm (default: HS256)
- `REQUEST_TIMEOUT`: HTTP request timeout in seconds (default: 30)
- `PORT`: Service port (default: 8080)

## Database Schema

### ledger-db Tables Used
- **transactions**: User transaction history
  - `amount`: Transaction amount in cents
  - `timestamp`: Transaction timestamp
  - `fromAccountNum`: Source account number
  - `toAccountNum`: Destination account number
  - `uuid`: Unique transaction identifier

## Deployment

### Docker
```bash
docker build -t user-tier-agent .
docker run -p 8080:8080 \
  -e LEDGER_DB_URI="postgresql://postgres:postgres@ledger-db:5432/postgresdb" \
  -e JWT_SECRET_KEY="your-secret-key" \
  -e GEMINI_API_KEY="your-gemini-key" \
  user-tier-agent
```

### Kubernetes
```bash
# Apply base configuration
kubectl apply -k k8s/base/

# Apply development overlay
kubectl apply -k k8s/overlays/development/
```

### Skaffold
```bash
# Development
skaffold dev --module user-tier-agent

# Production
skaffold run --module user-tier-agent
```

## Testing

### Unit Tests
```bash
cd tests
python -m pytest test_user_tier_agent.py -v
```

### Manual Testing
```bash
# Health check
curl http://localhost:8080/health

# Status check
curl http://localhost:8080/api/v1/status

# Allocation request
curl -X POST http://localhost:8080/api/v1/allocate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <jwt-token>" \
  -d '{
    "accountid": "1234567890",
    "amount": 1000.0,
    "uuid": "test-uuid",
    "purpose": "INVEST"
  }'
```

## Security

### Authentication
- JWT Bearer token required for all requests
- Token validation includes expiration and signature verification
- Account ID must match token payload

### Data Protection
- Database connections use encrypted connections
- Sensitive data (API keys) stored as Kubernetes secrets
- Input validation prevents injection attacks

### Network Security
- Service exposed only within cluster (ClusterIP)
- No external access without ingress configuration

## Monitoring

### Health Checks
- **Liveness Probe**: `/health` endpoint
- **Readiness Probe**: `/ready` endpoint (includes database connectivity)

### Logging
- Structured logging with service name and request IDs
- Request/response logging for audit trails
- Error logging with stack traces

### Metrics
- Allocation request success/failure rates
- AI response times and fallback usage
- Database query performance

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check `LEDGER_DB_URI` configuration
   - Verify ledger-db service is running
   - Check network connectivity

2. **Gemini API Errors**
   - Verify `GEMINI_API_KEY` is set correctly
   - Check API quota and rate limits
   - Service will fall back to default allocation

3. **JWT Token Validation Failed**
   - Verify `JWT_SECRET_KEY` matches token issuer
   - Check token expiration
   - Ensure proper Authorization header format

4. **Allocation Validation Failed**
   - Check AI response format
   - Verify percentages sum to 100
   - Review AI prompt and response parsing

### Debug Commands
```bash
# Check service status
kubectl get pods -l app=user-tier-agent

# View logs
kubectl logs -l app=user-tier-agent

# Test database connectivity
kubectl exec -it <pod-name> -- curl http://localhost:8080/ready

# Check configuration
kubectl describe deployment user-tier-agent
```

## Integration

### With Other Services
- **invest-svc**: Calls `/api/v1/allocate` for investment allocation
- **withdraw-svc**: Calls `/api/v1/allocate` for withdrawal allocation
- **ledgerwriter**: Provides transaction history for analysis

### Data Flow
```
User Request → invest-svc/withdraw-svc → user-tier-agent → ledger-db → Gemini AI → Response
```

## Performance

### Characteristics
- **Response Time**: < 2 seconds for typical requests
- **AI Processing**: 1-3 seconds depending on transaction history size
- **Fallback Time**: < 100ms when AI is unavailable
- **Concurrent Requests**: Supports multiple simultaneous allocations

### Optimization
- Database connection pooling
- AI response caching (future enhancement)
- Transaction history pagination
- Async processing for large histories

## Future Enhancements

### Planned Features
- **Machine Learning Models**: Custom ML models for allocation
- **User Preferences**: Allow users to set allocation preferences
- **Historical Analysis**: Long-term trend analysis
- **Real-time Market Data**: Incorporate market conditions

### Extension Points
- **Custom AI Models**: Support for different AI providers
- **Advanced Analytics**: More sophisticated transaction analysis
- **User Feedback Loop**: Learn from user behavior over time
- **Risk Assessment**: More granular risk profiling

## Contact and Support

### Service Owner
- **Team**: AI Services
- **Tier**: AI Agent
- **Application**: bank-of-anthos

### Documentation
- **README**: This file
- **API Docs**: Inline code documentation
- **LLM Documentation**: `llm.txt` for AI agent interaction

### Related Services
- **invest-svc**: Investment processing service
- **withdraw-svc**: Withdrawal processing service
- **ledger-db**: Transaction database
- **frontend**: User interface

---

*This service is part of the Bank of Anthos Investment Platform microservices architecture.*
