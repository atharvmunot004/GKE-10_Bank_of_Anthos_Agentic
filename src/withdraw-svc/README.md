# Withdraw Service (withdraw-svc)

The withdraw service handles user withdrawal requests from their investment portfolios in the Bank of Anthos system.

## Overview

The withdraw service processes withdrawal requests by:
1. Validating the user's portfolio has sufficient value
2. Getting tier allocation from the user-tier-agent
3. Creating withdrawal transaction records
4. Updating portfolio values by subtracting withdrawal amounts

## API Endpoints

### Health & Readiness
- `GET /health` - Service health check
- `GET /ready` - Service readiness check

### Withdrawal Operations
- `POST /api/v1/withdraw` - Process withdrawal request

## Withdrawal Process

### Request Format
```json
{
  "accountid": "1234567890",
  "amount": 1000.00
}
```

### Response Format
```json
{
  "status": "done",
  "accountid": "1234567890",
  "amount": 1000.00,
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "tier1": 600.0,
  "tier2": 300.0,
  "tier3": 100.0,
  "transaction_id": "transaction-uuid",
  "message": "Withdrawal processed successfully"
}
```

## Integration

### Dependencies
- **user-portfolio-db**: Portfolio value checking and updates
- **user-tier-agent**: Tier allocation for withdrawals

### Authentication
- Accepts JWT tokens in Authorization header
- Forwards tokens to user-tier-agent

## Environment Variables

- `USER_PORTFOLIO_DB_URI`: PostgreSQL connection string
- `USER_TIER_AGENT_URI`: User tier agent service URL
- `PORT`: Service port (default: 8080)
- `REQUEST_TIMEOUT`: HTTP request timeout (default: 30)

## Database Operations

### Portfolio Value Check
```sql
SELECT total_value FROM user_portfolios WHERE accountid = %s
```

### Transaction Creation
```sql
INSERT INTO portfolio_transactions (
  accountid, transaction_type, tier1_change, tier2_change, tier3_change,
  total_amount, fees, status, created_at, updated_at
) VALUES (
  %s, 'WITHDRAWAL', %s, %s, %s, %s, 0.0, 'PENDING', 
  CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
```

### Portfolio Update
```sql
UPDATE user_portfolios SET 
  tier1_value = tier1_value - %s,
  tier2_value = tier2_value - %s,
  tier3_value = tier3_value - %s,
  total_value = %s,
  updated_at = CURRENT_TIMESTAMP
WHERE accountid = %s
```

## Error Handling

### Insufficient Funds
```json
{
  "status": "failed",
  "error": "Insufficient portfolio value",
  "message": "Portfolio value 500.0 is less than withdrawal amount 1000.0"
}
```

### Invalid Request
```json
{
  "status": "failed",
  "error": "Invalid withdrawal data",
  "message": "Account ID and positive amount required"
}
```

## Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python withdraw_svc.py
```

### Docker
```bash
# Build image
docker build -t withdraw-svc .

# Run container
docker run -p 8080:8080 withdraw-svc
```

### Kubernetes
```bash
# Deploy with Skaffold
skaffold dev
```

## Testing

The service includes comprehensive unit tests covering:
- Portfolio value validation
- Tier allocation integration
- Transaction creation
- Portfolio updates
- Error handling scenarios

Run tests:
```bash
python -m pytest tests/
```
