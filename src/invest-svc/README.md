# Invest Service (invest-svc)

The invest-svc microservice handles investment processing by integrating with the user-tier-agent and updating the user-portfolio-db database.

## Overview

This service processes investment requests by:
1. Checking account balance via balancereader
2. Getting tier allocation from user-tier-agent
3. Creating/updating user portfolios in user-portfolio-db
4. Recording portfolio transactions

## API Endpoints

### POST /api/v1/invest
Process an investment request.

**Request:**
```json
{
  "account_number": "string",
  "amount": 1000.0
}
```

**Response:**
```json
{
  "status": "done",
  "portfolio_id": "uuid",
  "transaction_id": "uuid",
  "total_invested": 1000.0,
  "tier1_amount": 600.0,
  "tier2_amount": 300.0,
  "tier3_amount": 100.0,
  "message": "Investment processed successfully"
}
```

### GET /api/v1/portfolio/{user_id}
Get user portfolio information.

### GET /api/v1/portfolio/{user_id}/transactions
Get user portfolio transactions.

### GET /health
Health check endpoint.

### GET /ready
Readiness check endpoint.

## Environment Variables

- `USER_TIER_AGENT_URI`: User tier agent service URL (default: http://user-tier-agent:8080)
- `USER_PORTFOLIO_DB_URI`: Database connection string
- `BALANCE_READER_URI`: Balance reader service URL (default: http://balancereader:8080)
- `REQUEST_TIMEOUT`: Request timeout in seconds (default: 30)
- `PORT`: Service port (default: 8080)

## Dependencies

- **user-tier-agent**: For tier allocation calculations
- **balancereader**: For account balance verification
- **user-portfolio-db**: PostgreSQL database for portfolio data

## Deployment

### Using Kubernetes
```bash
kubectl apply -f kubernetes-manifests/invest-svc.yaml
```

### Using Skaffold (Development)
```bash
skaffold dev --module invest-svc
```

### Using Kustomize
```bash
kubectl apply -k k8s/overlays/development
```

## Testing

### Manual Testing
```bash
# Health check
curl http://invest-svc:8080/health

# Process investment
curl -X POST http://invest-svc:8080/api/v1/invest \
  -H "Content-Type: application/json" \
  -d '{"account_number": "1234567890", "amount": 1000.0}'
```

## Integration with investment-manager-svc

The invest-svc is called by investment-manager-svc with JWT authentication:

```python
# Investment flow
investment-manager-svc → invest-svc → user-tier-agent
                     ↓
                  user-portfolio-db
```

The service expects JWT tokens to be forwarded from the investment-manager-svc for authentication with external services.
