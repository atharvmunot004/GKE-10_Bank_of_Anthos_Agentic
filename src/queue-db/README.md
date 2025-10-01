# Queue Database Service

The `queue-db` is a PostgreSQL database service that stores investment and withdrawal requests for the Bank of Anthos portfolio management system. It provides a combined queue for investment and withdrawal operations with UUID consistency and transaction type tracking.

## Overview

This microservice manages a queue system for portfolio management operations, allowing users to submit investment and withdrawal requests that are processed asynchronously. The database maintains data consistency and provides efficient querying capabilities for queue management.

## Features

- **PostgreSQL Database**: Robust, ACID-compliant database for queue management
- **Investment & Withdrawal Queues**: Unified queue system with transaction type differentiation
- **UUID Consistency**: Unique identifiers across all queue operations
- **Status Tracking**: Comprehensive status management (PENDING, PROCESSING, COMPLETED, FAILED, CANCELLED)
- **Tier-based Investments**: Support for three investment tiers (Conservative, Moderate, Aggressive)
- **Performance Optimization**: Indexed queries and efficient data structures
- **Health Monitoring**: Built-in health checks and monitoring capabilities

## Database Schema

### Main Table: `investment_withdrawal_queue`

| Column | Type | Description |
|--------|------|-------------|
| `queue_id` | SERIAL PRIMARY KEY | Auto-incrementing unique identifier |
| `accountid` | VARCHAR(20) NOT NULL | Bank account number making the request |
| `tier_1` | DECIMAL(20, 8) NOT NULL | Amount for Tier 1 (Conservative investments) |
| `tier_2` | DECIMAL(20, 8) NOT NULL | Amount for Tier 2 (Moderate investments) |
| `tier_3` | DECIMAL(20, 8) NOT NULL | Amount for Tier 3 (Aggressive investments) |
| `uuid` | VARCHAR(36) UNIQUE NOT NULL | Unique identifier for the queue entry |
| `transaction_type` | VARCHAR(20) NOT NULL | Transaction type: 'INVEST' or 'WITHDRAW' |
| `status` | VARCHAR(20) NOT NULL | Processing status |
| `created_at` | TIMESTAMP WITH TIME ZONE | When request was created |
| `updated_at` | TIMESTAMP WITH TIME ZONE | When request was last updated |
| `processed_at` | TIMESTAMP WITH TIME ZONE | When request was processed |

### Views

- **`queue_statistics`**: Aggregated statistics by status and transaction type
- **`account_queue_summary`**: Per-account queue summary and totals

## Connection Details

- **Service Name**: `queue-db`
- **Port**: `5432`
- **Database**: `queue-db`
- **Username**: `queue-admin`
- **Password**: `queue-pwd`
- **Connection String**: `postgresql://queue-admin:queue-pwd@queue-db:5432/queue-db`

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `QUEUE_DB_URI` | Full database connection URI | `postgresql://queue-admin:queue-pwd@queue-db:5432/queue-db` |
| `POSTGRES_DB` | Database name | `queue-db` |
| `POSTGRES_USER` | Database username | `queue-admin` |
| `POSTGRES_PASSWORD` | Database password | `queue-pwd` |

## API Endpoints (Conceptual)

While this is a database service, the following endpoints would typically be implemented by a service layer:

### Queue Management
- `POST /queue/investment` - Create investment request
- `POST /queue/withdrawal` - Create withdrawal request
- `GET /queue/{uuid}` - Get queue entry by UUID
- `GET /queue/account/{accountid}` - Get all requests for account
- `PUT /queue/{uuid}/status` - Update request status
- `DELETE /queue/{uuid}` - Cancel/delete request

### Admin Endpoints
- `GET /queue/stats` - Get queue statistics
- `GET /queue/health` - Health check endpoint
- `GET /queue/metrics` - Prometheus metrics

## Business Logic

### Status Transitions
- `PENDING` → `PROCESSING`, `CANCELLED`
- `PROCESSING` → `COMPLETED`, `FAILED`
- `COMPLETED` → (terminal state)
- `FAILED` → `PENDING`, `CANCELLED`
- `CANCELLED` → (terminal state)

### Validation Rules
- Account ID must be valid format
- Tier amounts must be non-negative
- Transaction type must be INVEST or WITHDRAW
- UUID must be unique across all requests
- For withdrawals, total amount must not exceed account balance

## Development

### Prerequisites
- Docker
- Kubernetes cluster (local or cloud)
- Skaffold (for local development)

### Local Development with Skaffold

1. **Start the service**:
   ```bash
   skaffold dev
   ```

2. **Port forwarding**: The service will be available on `localhost:5432`

3. **View logs**:
   ```bash
   kubectl logs -f deployment/queue-db
   ```

### Manual Deployment

1. **Build the Docker image**:
   ```bash
   docker build -t queue-db .
   ```

2. **Apply Kubernetes manifests**:
   ```bash
   kubectl apply -f k8s/overlays/development/
   ```

3. **Check deployment status**:
   ```bash
   kubectl get pods -l app=queue-db
   kubectl get services -l app=queue-db
   ```

## Testing

### Unit Tests
The service includes comprehensive unit tests covering:
- Database schema validation
- Business logic validation
- Error handling
- Data model serialization/deserialization
- Constraint validation
- Status update tests

### Integration Tests
- End-to-end request creation and processing
- Database transaction rollback on errors
- Concurrent request handling
- Database connection pooling
- Performance under load
- Data consistency across operations

### Test Data
Sample test data is automatically loaded during initialization, including:
- Investment requests in various states
- Withdrawal requests in various states
- Different account IDs for testing
- Realistic tier allocations

## Monitoring

### Health Checks
- **Liveness**: Database connectivity check
- **Readiness**: Service initialization complete
- **Startup**: Database schema validation

### Metrics
- Queue size (pending requests)
- Processing rate (requests per minute)
- Error rate (failed requests percentage)
- Average processing time
- Database connections
- Response time percentiles

### Logging
- Structured JSON logging with correlation IDs
- Log levels: ERROR, WARN, INFO, DEBUG
- Categories: Request processing, Database operations, Error conditions, Performance metrics

## Deployment

### Kubernetes Resources
- **StatefulSet**: For persistent database storage
- **Service**: ClusterIP for internal communication
- **ConfigMap**: Database configuration
- **Secret**: Database credentials (in production)
- **PersistentVolumeClaim**: Database storage

### Resource Requirements
- **CPU**: 500m (request), 1000m (limit)
- **Memory**: 1Gi (request), 2Gi (limit)
- **Storage**: 10Gi persistent volume

### Security
- Network policies for restricted database access
- Pod security policies for non-root execution
- Secret management for credentials

## Inter-Service Communication

### Upstream Services
- **user-service**: Validate account existence and balance
- **portfolio-service**: Get current portfolio allocation
- **notification-service**: Send status updates

### Downstream Services
- **investment-processor**: Process investment requests
- **withdrawal-processor**: Process withdrawal requests
- **audit-service**: Log all queue operations

## Performance Optimization

### Database Optimization
- Proper indexing strategy for common queries
- Query optimization for complex operations
- Connection pooling for efficient resource usage
- Read replicas for reporting (future enhancement)

### Caching Strategy
- Redis cache for frequently accessed queue statistics
- Application cache for account validation results
- 5-minute TTL for account data

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check if the StatefulSet is running
   - Verify network policies
   - Check resource limits

2. **Schema Initialization Failed**
   - Check init container logs
   - Verify SQL syntax
   - Check file permissions

3. **Performance Issues**
   - Monitor resource usage
   - Check query performance
   - Review indexing strategy

### Debug Commands

```bash
# Check pod status
kubectl get pods -l app=queue-db

# View logs
kubectl logs -f statefulset/queue-db

# Connect to database
kubectl exec -it queue-db-0 -- psql -U queue-admin -d queue-db

# Check resource usage
kubectl top pod -l app=queue-db
```

## License

Copyright 2024 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
