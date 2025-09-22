# Consistency Manager Service

The `consistency-manager-svc` ensures UUID consistency between the queue-db and portfolio-transaction table. It monitors queue status updates and synchronizes them with portfolio transaction records.

## Overview

This service acts as a bridge between the queue management system and the portfolio transaction system, ensuring that:

1. **UUID Consistency**: All transactions maintain the same UUID from origination to completion
2. **Status Synchronization**: Queue status updates are reflected in portfolio transactions
3. **Data Integrity**: Portfolio transactions are created/updated based on queue entries
4. **Real-time Sync**: Background synchronization keeps data consistent

## Features

- **Automatic Sync**: Background thread syncs queue entries to portfolio transactions
- **Manual Sync**: API endpoint for manual synchronization triggers
- **Health Monitoring**: Health and readiness checks for Kubernetes
- **Statistics**: API endpoint for monitoring sync statistics
- **Error Handling**: Robust error handling and logging
- **Configurable**: Adjustable sync interval and batch size

## API Endpoints

### Health Check
- **GET** `/health` - Service health status
- **GET** `/ready` - Service readiness status

### Operations
- **POST** `/api/v1/sync` - Manually trigger sync operation
- **GET** `/api/v1/stats` - Get synchronization statistics

## Environment Variables

- `QUEUE_DB_URI`: Connection string for queue-db
- `USER_PORTFOLIO_DB_URI`: Connection string for user-portfolio-db
- `PORT`: Service port (default: 8080)
- `SYNC_INTERVAL`: Sync interval in seconds (default: 30)
- `BATCH_SIZE`: Number of entries to process per sync (default: 100)

## Database Schema

### Queue Database (queue-db)
- `investment_queue`: Investment requests
- `withdrawal_queue`: Withdrawal requests

### Portfolio Database (user-portfolio-db)
- `portfolio_transactions`: Portfolio transaction records

## Synchronization Logic

1. **Monitor Queues**: Periodically check for processed queue entries
2. **Check Existence**: Verify if portfolio transaction already exists
3. **Create/Update**: Create new transactions or update existing ones
4. **Status Sync**: Ensure status consistency between systems
5. **Error Handling**: Log and track synchronization errors

## Deployment

### Using Skaffold
```bash
# Deploy to development
skaffold dev --module consistency-manager-svc

# Deploy to production
skaffold run --module consistency-manager-svc --profile prod
```

### Using kubectl
```bash
# Deploy using Kustomize
kubectl apply -k k8s/overlays/development

# Deploy using standalone manifest
kubectl apply -f ../../kubernetes-manifests/consistency-manager-svc.yaml
```

## Monitoring

### Health Checks
```bash
# Check service health
curl http://consistency-manager-svc:8080/health

# Check service readiness
curl http://consistency-manager-svc:8080/ready
```

### Statistics
```bash
# Get sync statistics
curl http://consistency-manager-svc:8080/api/v1/stats
```

### Manual Sync
```bash
# Trigger manual sync
curl -X POST http://consistency-manager-svc:8080/api/v1/sync
```

## Configuration

### Development
- Sync interval: 15 seconds
- Batch size: 50 entries
- More frequent synchronization for testing

### Production
- Sync interval: 30 seconds
- Batch size: 100 entries
- Optimized for performance

## Dependencies

- **queue-db**: Source of queue entries
- **user-portfolio-db**: Target for portfolio transactions
- **PostgreSQL**: Database connections
- **Flask**: Web framework

## Testing

Unit tests are available in the `tests/` directory:

```bash
# Run unit tests
cd tests
python -m pytest test_consistency_manager.py -v

# Run integration tests
python -m pytest test_integration.py -v
```

## Logging

The service provides comprehensive logging:

- **INFO**: Normal operation and sync statistics
- **WARNING**: Non-critical issues
- **ERROR**: Sync failures and database errors
- **DEBUG**: Detailed operation tracing

## Security

- **Non-root user**: Runs as user 1000
- **Read-only filesystem**: Security best practices
- **Resource limits**: CPU and memory constraints
- **Network policies**: Controlled database access

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check database service availability
   - Verify connection strings
   - Check network policies

2. **Sync Not Working**
   - Check service logs
   - Verify database permissions
   - Test manual sync endpoint

3. **High Memory Usage**
   - Reduce batch size
   - Increase sync interval
   - Check for memory leaks

### Debug Commands

```bash
# Check service logs
kubectl logs -f deployment/consistency-manager-svc

# Check service status
kubectl describe deployment consistency-manager-svc

# Test database connectivity
kubectl exec -it deployment/consistency-manager-svc -- python -c "
import psycopg2
conn = psycopg2.connect('postgresql://queue-admin:queue-pwd@queue-db:5432/queue-db')
print('Queue DB connected')
conn.close()
"
```

## Future Enhancements

- **Metrics**: Prometheus metrics for monitoring
- **Alerting**: Alerts for sync failures
- **Retry Logic**: Automatic retry for failed syncs
- **Batch Processing**: More efficient batch operations
- **Real-time Updates**: WebSocket-based real-time updates
