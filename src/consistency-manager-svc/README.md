# Consistency Manager Service

A microservice that runs continuously to maintain consistency between queue-db and user-portfolio-db by synchronizing transaction statuses and updating portfolio values based on market changes.

## Overview

The Consistency Manager Service ensures data consistency across the investment and withdrawal queue systems by:

1. **Monitoring Market Changes**: Calculates delta values for tier market value changes
2. **Processing Investment Queue**: Updates portfolio values for completed investments
3. **Processing Withdrawal Queue**: Updates portfolio allocations for completed withdrawals
4. **Status Synchronization**: Keeps transaction statuses in sync between databases

## Features

- **Continuous Operation**: Runs in background without manual triggers
- **Market-Based Updates**: Adjusts portfolio values based on tier market value changes
- **Dual Database Support**: Manages consistency between queue-db and user-portfolio-db
- **Real-time Processing**: Processes queue entries as they are updated
- **Health Monitoring**: Provides health and readiness endpoints

## API Endpoints

### Health & Monitoring
- `GET /health` - Service health check
- `GET /ready` - Service readiness check
- `GET /api/v1/consistency/status` - Get current consistency status

### Manual Operations
- `POST /api/v1/consistency/trigger` - Manually trigger consistency cycle
- `POST /api/v1/consistency/update-tier-values` - Update tier values

## Environment Variables

### Database Configuration
- `QUEUE_DB_URI`: PostgreSQL connection string for queue-db
- `USER_PORTFOLIO_DB_URI`: PostgreSQL connection string for user-portfolio-db

### Service Configuration
- `POLLING_INTERVAL`: Consistency check interval in seconds (default: 30)
- `PORT`: Service port (default: 8080)

### Tier Values
- `TIER1`: Tier 1 pool value (default: 1000000.0)
- `TIER1_MV`: Tier 1 market value (default: 1000000.0)
- `TIER2`: Tier 2 pool value (default: 2000000.0)
- `TIER2_MV`: Tier 2 market value (default: 2000000.0)
- `TIER3`: Tier 3 pool value (default: 500000.0)
- `TIER3_MV`: Tier 3 market value (default: 500000.0)

## Consistency Process

### Step 1: Calculate Delta Values
```
del_t1_mv = ((TIER1_MV - TIER1) / TIER1)
del_t2_mv = ((TIER2_MV - TIER2) / TIER2)
del_t3_mv = ((TIER3_MV - TIER3) / TIER3)
```

### Step 2-4: Process Investment Queue
1. Query investment_queue for entries updated since last check
2. Update portfolio_transactions status to 'PROCESSED'
3. For COMPLETED entries, update portfolio tier values:
   ```
   tier1_value = tier1_value * (1 + del_t1_mv)
   tier2_value = tier2_value * (1 + del_t2_mv)
   tier3_value = tier3_value * (1 + del_t3_mv)
   ```

### Step 5-7: Process Withdrawal Queue
1. Query withdrawal_queue for entries updated since last check
2. Update portfolio_transactions status to 'PROCESSED'
3. For COMPLETED entries, update portfolio tier allocations:
   ```
   tier1_allocation = tier1_allocation * (1 - del_t1_mv)
   tier2_allocation = tier2_allocation * (1 - del_t2_mv)
   tier3_allocation = tier3_allocation * (1 - del_t3_mv)
   ```

### Step 8: Update Timestamp
Update the last processed timestamp to CURRENT_TIMESTAMP

## Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export QUEUE_DB_URI="postgresql://queue-admin:queue-pwd@localhost:5432/queue-db"
export USER_PORTFOLIO_DB_URI="postgresql://portfolio-admin:portfolio-pwd@localhost:5432/user-portfolio-db"

# Run the service
python consistency_manager_svc.py
```

### Testing
```bash
# Run unit tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_consistency_manager_svc.py -v
```

### Docker
```bash
# Build image
docker build -t consistency-manager-svc .

# Run container
docker run -p 8080:8080 consistency-manager-svc
```

## Deployment

### Kubernetes
```bash
# Deploy to development
kubectl apply -k k8s/overlays/development

# Deploy to production
kubectl apply -k k8s/overlays/production
```

### Skaffold
```bash
# Run with Skaffold
skaffold run
```

## Monitoring

### Health Checks
- **Liveness Probe**: `/health` endpoint
- **Readiness Probe**: `/ready` endpoint
- **Consistency Status**: `/api/v1/consistency/status`

### Logging
The service provides comprehensive logging for:
- Consistency cycle execution
- Database operations
- Error handling
- Performance metrics

## Integration

### Dependencies
- **queue-db**: PostgreSQL database for investment and withdrawal queues
- **user-portfolio-db**: PostgreSQL database for portfolio data
- **execute-order-svc**: For tier value updates
- **user-request-queue-svc**: For queue processing

### Data Flow
1. **Market Changes**: execute-order-svc updates TIER1_MV, TIER2_MV, TIER3_MV
2. **Queue Processing**: user-request-queue-svc processes investment/withdrawal requests
3. **Consistency Management**: This service maintains consistency between databases
4. **Portfolio Updates**: Portfolio values and allocations are updated based on market changes

## Architecture

```
┌─────────────────────┐    ┌──────────────────────┐
│   queue-db          │    │  user-portfolio-db   │
│                     │    │                      │
│ • investment_queue  │◄──►│ • user_portfolios    │
│ • withdrawal_queue  │    │ • portfolio_transactions │
└─────────────────────┘    └──────────────────────┘
           ▲                          ▲
           │                          │
           └─────── consistency-manager-svc ──────┘
```

## Performance

- **Polling Interval**: Configurable (default 30 seconds)
- **Database Connections**: Efficient connection pooling
- **Error Handling**: Graceful degradation and retry logic
- **Resource Usage**: Optimized for continuous operation

## Security

- **Non-root User**: Container runs as non-root user
- **Database Security**: Uses connection strings with credentials
- **Input Validation**: Validates all input parameters
- **Error Handling**: Secure error messages without sensitive data exposure