# User Request Queue Service (user-request-queue-svc)

The user request queue service manages a batch processing queue for investment and withdrawal requests in the Bank of Anthos system.

## Overview

The service implements a sophisticated batching mechanism that:
1. Collects individual requests until a batch size is reached
2. Aggregates tier values across all requests in the batch
3. Processes the batch through the bank-asset-agent
4. Updates all requests in the batch based on the processing result

## API Endpoints

### Health & Readiness
- `GET /health` - Service health check
- `GET /ready` - Service readiness check

### Queue Operations
- `POST /api/v1/queue` - Add request to processing queue
- `GET /api/v1/queue/status/<uuid>` - Get request status
- `GET /api/v1/queue/stats` - Get queue statistics

## Queue Processing Flow

### 1. Request Addition
```json
{
  "uuid": "request-uuid",
  "tier1": 600.0,
  "tier2": 300.0,
  "tier3": 100.0,
  "purpose": "INVEST",
  "accountid": "1234567890"
}
```

### 2. Batch Processing
When 10 requests are collected:
- Calculate aggregate tiers (T1, T2, T3)
- Call bank-asset-agent with aggregate values
- Update all requests based on response

### 3. Status Updates
- `PROCESSING` - Request queued, waiting for batch
- `DONE` - Successfully processed
- `FAILED` - Processing failed

## Batch Processing Logic

### Aggregate Calculation
```python
# For INVEST requests: Add to totals
T1 += tier1
T2 += tier2  
T3 += tier3

# For WITHDRAW requests: Subtract from totals
T1 -= tier1
T2 -= tier2
T3 -= tier3
```

### Bank Asset Agent Call
```json
{
  "T1": 5000.0,
  "T2": 3000.0,
  "T3": 2000.0
}
```

## Integration

### Dependencies
- **queue-db**: PostgreSQL database for request storage
- **bank-asset-agent**: External service for batch processing

### Background Processing
- Continuous polling for pending requests
- Automatic batch formation when size threshold is reached
- Thread-safe processing with locks

## Environment Variables

- `QUEUE_DB_URI`: PostgreSQL connection string
- `BANK_ASSET_AGENT_URI`: Bank asset agent service URL
- `BATCH_SIZE`: Number of requests per batch (default: 10)
- `REQUEST_TIMEOUT`: HTTP request timeout (default: 30)
- `POLLING_INTERVAL`: Background polling interval (default: 5)
- `PORT`: Service port (default: 8080)

## Database Operations

### Request Storage
```sql
INSERT INTO withdrawal_queue (
  uuid, accountid, tier1, tier2, tier3, purpose, status, created_at, updated_at
) VALUES (
  %s, %s, %s, %s, %s, %s, 'PROCESSING', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
```

### Batch Retrieval
```sql
SELECT uuid, accountid, tier1, tier2, tier3, purpose
FROM withdrawal_queue 
WHERE status = 'PROCESSING'
ORDER BY created_at ASC
LIMIT %s
```

### Status Updates
```sql
UPDATE withdrawal_queue 
SET status = %s, updated_at = CURRENT_TIMESTAMP
WHERE uuid = %s
```

## Error Handling

### Request Validation
- Missing required fields (400)
- Invalid purpose values (400)
- Invalid tier values (400)

### Processing Errors
- Database connection failures (500)
- Bank asset agent failures (500)
- Batch processing errors (500)

## Monitoring

### Queue Statistics
```json
{
  "total_requests": 150,
  "processing": 8,
  "completed": 140,
  "failed": 2
}
```

### Request Status
```json
{
  "uuid": "request-uuid",
  "accountid": "1234567890",
  "tier1": 600.0,
  "tier2": 300.0,
  "tier3": 100.0,
  "purpose": "INVEST",
  "status": "DONE",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:05:00Z"
}
```

## Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python user_request_queue_svc.py
```

### Docker
```bash
# Build image
docker build -t user-request-queue-svc .

# Run container
docker run -p 8080:8080 user-request-queue-svc
```

### Kubernetes
```bash
# Deploy with Skaffold
skaffold dev
```

## Testing

The service includes comprehensive unit tests covering:
- Request validation and queuing
- Batch processing logic
- Database operations
- Error handling scenarios
- Background processing

Run tests:
```bash
python -m pytest tests/
```

## Performance Considerations

### Batch Size Optimization
- Configurable batch size for optimal throughput
- Balance between latency and efficiency
- Default batch size of 10 requests

### Background Processing
- Non-blocking request handling
- Efficient polling mechanism
- Thread-safe operations

### Database Optimization
- Indexed queries for fast retrieval
- Efficient status updates
- Connection pooling
