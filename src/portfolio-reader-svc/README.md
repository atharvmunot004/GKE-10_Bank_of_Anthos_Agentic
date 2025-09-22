# Portfolio Reader Service

A microservice for reading and retrieving portfolio information from the user-portfolio-db.

## Overview

The Portfolio Reader Service provides read-only access to user portfolio data, including:
- Portfolio information (allocations, values, timestamps)
- Transaction history
- Portfolio analytics and summaries

## API Endpoints

### Health Checks
- `GET /health` - Health check endpoint
- `GET /ready` - Readiness check endpoint

### Portfolio Operations
- `GET /api/v1/portfolio/{user_id}` - Get portfolio with recent transactions
- `GET /api/v1/portfolio/{user_id}/transactions` - Get portfolio transactions (with pagination)
- `GET /api/v1/portfolio/{user_id}/summary` - Get portfolio summary with analytics

## Environment Variables

- `USER_PORTFOLIO_DB_URI` - PostgreSQL connection string (default: postgresql://portfolio-admin:portfolio-pwd@user-portfolio-db:5432/user-portfolio-db)
- `PORT` - Service port (default: 8080)

## Database Schema

The service connects to the user-portfolio-db and reads from:
- `user_portfolios` table - Portfolio allocations and values
- `portfolio_transactions` table - Transaction history

## Response Format

### Portfolio Response
```json
{
  "portfolio": {
    "accountid": "1234567890",
    "currency": "USD",
    "tier1_allocation": 60.0,
    "tier2_allocation": 30.0,
    "tier3_allocation": 10.0,
    "total_allocation": 100.0,
    "tier1_value": 6000.0,
    "tier2_value": 3000.0,
    "tier3_value": 1000.0,
    "total_value": 10000.0,
    "created_at": "2024-01-01T10:00:00Z",
    "updated_at": "2024-01-01T10:05:00Z"
  },
  "transactions": [
    {
      "id": "uuid-here",
      "transaction_type": "INVEST",
      "tier1_change": 600.0,
      "tier2_change": 300.0,
      "tier3_change": 100.0,
      "total_amount": 1000.0,
      "fees": 0.0,
      "status": "COMPLETED",
      "created_at": "2024-01-01T10:00:00Z",
      "updated_at": "2024-01-01T10:05:00Z"
    }
  ]
}
```

### Portfolio Summary Response
```json
{
  "accountid": "1234567890",
  "currency": "USD",
  "current_value": {
    "total_value": 10000.0,
    "tier1_value": 6000.0,
    "tier2_value": 3000.0,
    "tier3_value": 1000.0
  },
  "allocation": {
    "tier1_allocation": 60.0,
    "tier2_allocation": 30.0,
    "tier3_allocation": 10.0,
    "total_allocation": 100.0
  },
  "analytics": {
    "total_invested": 9500.0,
    "total_gain_loss": 500.0,
    "gain_loss_percentage": 5.26,
    "total_transactions": 5,
    "invest_count": 4,
    "withdrawal_count": 1,
    "completed_count": 5
  },
  "timestamps": {
    "created_at": "2024-01-01T10:00:00Z",
    "updated_at": "2024-01-01T10:05:00Z"
  }
}
```

## Deployment

### Using kubectl
```bash
kubectl apply -f kubernetes-manifests/portfolio-reader-svc.yaml
```

### Using Skaffold
```bash
skaffold dev
```

### Using Kustomize
```bash
kubectl apply -k src/portfolio-reader-svc/k8s/overlays/development/
```

## Dependencies

- PostgreSQL database (user-portfolio-db)
- Flask web framework
- psycopg2 for database connectivity

## Error Handling

The service returns appropriate HTTP status codes:
- 200: Success
- 404: Portfolio not found
- 500: Internal server error

All errors include a JSON response with error details.
