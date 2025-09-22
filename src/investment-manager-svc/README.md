# Investment Manager Service

An orchestration service that manages user investment portfolios by integrating with multiple backend services. It acts as the central API layer for investment operations, handling portfolio data retrieval, investment processing, and withdrawal operations.

## Features

- **Portfolio Management**: Retrieve portfolio information and transaction history
- **Investment Processing**: Process investment requests with tier-based allocation
- **Withdrawal Processing**: Handle withdrawal requests with proportional distribution
- **Service Orchestration**: Coordinate calls to multiple backend services
- **Transaction Recording**: Automatically record transactions in ledger-db
- **Error Handling**: Comprehensive error handling and logging

## Architecture

The Investment Manager Service acts as an orchestration layer that:

1. **Retrieves Portfolio Data**: Calls portfolio-reader-svc to get current portfolio information
2. **Processes Investments**: Calls invest-svc to handle investment requests
3. **Processes Withdrawals**: Calls withdraw-svc to handle withdrawal requests
4. **Records Transactions**: Calls ledger-writer to record financial transactions

## API Endpoints

### Health and Status
- `GET /health` - Health check endpoint
- `GET /ready` - Readiness probe endpoint
- `GET /api/v1/status` - Service status and dependency health

### Portfolio Management
- `GET /api/v1/portfolio/{account_id}` - Get portfolio information
- `GET /api/v1/portfolio/{account_id}/transactions` - Get portfolio transactions

### Investment Operations
- `POST /api/v1/invest` - Process investment request
- `POST /api/v1/withdraw` - Process withdrawal request

## Request/Response Examples

### Get Portfolio
```bash
curl -X GET http://localhost:8080/api/v1/portfolio/1234567890
```

Response:
```json
{
  "portfolio": {
    "accountid": "1234567890",
    "tier1_allocation": 60.0,
    "tier2_allocation": 30.0,
    "tier3_allocation": 10.0,
    "tier1_value": 6000.00,
    "tier2_value": 3000.00,
    "tier3_value": 1000.00
  },
  "transactions": [
    {
      "uuid": "transaction-uuid-1",
      "tier1_change": 100.00,
      "tier2_change": 50.00,
      "tier3_change": 25.00,
      "status": "COMPLETED"
    }
  ]
}
```

### Process Investment
```bash
curl -X POST http://localhost:8080/api/v1/invest \
  -H "Content-Type: application/json" \
  -d '{"accountid": "1234567890", "amount": 1000.0}'
```

Response:
```json
{
  "status": "success",
  "message": "Investment processed and recorded successfully",
  "account_id": "1234567890",
  "amount": 1000.0,
  "ledger_recorded": true
}
```

### Process Withdrawal
```bash
curl -X POST http://localhost:8080/api/v1/withdraw \
  -H "Content-Type: application/json" \
  -d '{"accountid": "1234567890", "amount": 500.0}'
```

Response:
```json
{
  "status": "success",
  "message": "Withdrawal processed and recorded successfully",
  "account_id": "1234567890",
  "amount": 500.0,
  "ledger_recorded": true
}
```

## Service Dependencies

### Portfolio Reader Service
- **Purpose**: Retrieves portfolio data and transaction history
- **Endpoint**: `http://portfolio-reader-svc:8080`
- **Environment Variable**: `PORTFOLIO_READER_URI`

### Investment Service
- **Purpose**: Processes investment requests
- **Endpoint**: `http://invest-svc:8080`
- **Environment Variable**: `INVEST_SVC_URI`

### Withdrawal Service
- **Purpose**: Processes withdrawal requests
- **Endpoint**: `http://withdraw-svc:8080`
- **Environment Variable**: `WITHDRAW_SVC_URI`

### Ledger Writer Service
- **Purpose**: Records financial transactions in ledger-db
- **Endpoint**: `http://ledgerwriter:8080`
- **Environment Variable**: `LEDGER_WRITER_URI`

## Environment Variables

- `PORT`: Service port (default: 8080)
- `PORTFOLIO_READER_URI`: Portfolio reader service URL
- `INVEST_SVC_URI`: Investment service URL
- `WITHDRAW_SVC_URI`: Withdrawal service URL
- `LEDGER_WRITER_URI`: Ledger writer service URL
- `LOCAL_ROUTING_NUM`: Bank routing number
- `REQUEST_TIMEOUT`: Request timeout in seconds (default: 30)

## Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export PORTFOLIO_READER_URI=http://localhost:8081
export INVEST_SVC_URI=http://localhost:8082
export WITHDRAW_SVC_URI=http://localhost:8083
export LEDGER_WRITER_URI=http://localhost:8084
export LOCAL_ROUTING_NUM=123456789

# Run the service
python investment_manager.py
```

### Docker
```bash
# Build image
docker build -t investment-manager-svc .

# Run container
docker run -p 8080:8080 \
  -e PORTFOLIO_READER_URI=http://portfolio-reader-svc:8080 \
  -e INVEST_SVC_URI=http://invest-svc:8080 \
  -e WITHDRAW_SVC_URI=http://withdraw-svc:8080 \
  -e LEDGER_WRITER_URI=http://ledgerwriter:8080 \
  investment-manager-svc
```

## Testing

```bash
# Run tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=investment_manager

# Test specific endpoint
curl -X GET http://localhost:8080/api/v1/status
```

## Deployment

### Kubernetes
```bash
# Apply manifests
kubectl apply -f kubernetes-manifests/investment-manager-svc.yaml

# Check status
kubectl get pods -l app=investment-manager-svc

# Check logs
kubectl logs -l app=investment-manager-svc
```

### Skaffold
```bash
# Deploy with Skaffold
skaffold dev --module investment-manager-svc

# Deploy to specific environment
skaffold run --module investment-manager-svc -p development
```

## Monitoring and Observability

- **Health Checks**: `/health` and `/ready` endpoints
- **Dependency Status**: `/api/v1/status` shows all service dependencies
- **Logging**: Comprehensive logging for all operations
- **Error Tracking**: Detailed error logging and monitoring
- **Performance Metrics**: Request/response tracking

## Error Handling

- **Service Unavailable**: Returns 503 when dependent services are down
- **Invalid Data**: Returns 400 for malformed requests
- **Investment/Withdrawal Failures**: Returns 400 with error details
- **Partial Success**: Returns 200 with warning when ledger recording fails

## Security

- **No Direct Database Access**: Acts as API gateway only
- **Service Authentication**: Relies on internal service mesh
- **Input Validation**: Validates all incoming requests
- **Error Sanitization**: Prevents sensitive data leakage in errors

## Performance Considerations

- **Connection Pooling**: Uses requests library with connection reuse
- **Timeout Handling**: Configurable timeouts for all external calls
- **Circuit Breaker Pattern**: Graceful degradation when services are unavailable
- **Resource Limits**: CPU and memory limits configured in Kubernetes

## Troubleshooting

- **Check Dependencies**: Use `/api/v1/status` to verify service health
- **Review Logs**: Check application logs for error details
- **Verify Configuration**: Ensure all environment variables are set
- **Test Connectivity**: Verify network connectivity to dependent services

## Integration

This service integrates with:
- **Frontend**: Provides API endpoints for portfolio management
- **Portfolio Reader Service**: Retrieves portfolio data
- **Investment Service**: Processes investment operations
- **Withdrawal Service**: Processes withdrawal operations
- **Ledger Writer Service**: Records financial transactions