# Execute Order Service (execute-order-svc)

The execute order service processes buy and sell orders for assets in the Bank of Anthos trading system, managing asset inventory and executing trades based on realistic market conditions.

## Overview

The service handles order execution for different asset types across three tiers, managing pool funds, calculating execution probabilities, and updating asset inventories in the assets-db.

## Supported Operations

### Order Types
- **BUY**: Purchase assets using tier pool funds
- **SELL**: Sell assets from existing inventory

### Asset Tiers
- **Tier 1**: High-risk assets (cryptocurrencies)
- **Tier 2**: Medium-risk assets (ETFs, mutual funds, equities)
- **Tier 3**: Low-risk assets (bonds, stable investments)

## API Endpoints

### Health & Readiness
- `GET /health` - Service health check
- `GET /ready` - Service readiness check

### Order Operations
- `POST /api/v1/execute-order` - Execute buy or sell orders
- `GET /api/v1/tier-status` - Get current tier pool and market value status

## Order Execution Request

### Request Format
```json
{
  "asset_id": "BTC001",
  "asset_type": "CRYPTO",
  "tier_number": 1,
  "asset_name": "Bitcoin",
  "amount_trade": 100.0,
  "price": 50000.0,
  "purpose": "BUY"
}
```

### Response Format

#### Successful Execution
```json
{
  "status": "executed",
  "order_id": "uuid-string",
  "asset_id": "BTC001",
  "asset_name": "Bitcoin",
  "amount_traded": 100.0,
  "price_executed": 50000.0,
  "total_value": 5000000.0,
  "new_amount": 100.0,
  "execution_probability": 0.85,
  "message": "BUY order executed successfully",
  "timestamp": "2024-01-01T10:00:00Z",
  "tier_number": 1,
  "asset_type": "CRYPTO",
  "updated_tier_values": {
    "TIER1_MV": 5000000.0,
    "TIER2_MV": 2000000.0,
    "TIER3_MV": 500000.0
  }
}
```

#### Failed Execution
```json
{
  "status": "failed",
  "error": "insufficient_funds",
  "message": "Insufficient funds in tier 1 pool. Required: 5000000, Available: 1000000",
  "required_amount": 5000000.0,
  "available_amount": 1000000.0,
  "timestamp": "2024-01-01T10:00:00Z",
  "tier_number": 1,
  "asset_type": "CRYPTO"
}
```

## Order Execution Logic

### BUY Orders
1. **Fund Check**: Verify sufficient funds in tier pool
2. **Asset Lookup**: Check if asset exists in assets-db
3. **Probability Calculation**: Calculate execution probability based on:
   - Price difference between request and market
   - Volume ratio between request and available
   - Market liquidity conditions
4. **Execution Decision**: Execute if random probability check passes
5. **Database Update**: Update asset amount or create new asset

### SELL Orders
1. **Asset Check**: Verify asset exists in assets-db
2. **Inventory Check**: Verify sufficient assets to sell
3. **Probability Calculation**: Calculate execution probability
4. **Execution Decision**: Execute if random probability check passes
5. **Database Update**: Update asset amount (reduce inventory)

## Environment Variables

### Tier Pool Configuration
- `TIER1`: Available funds for tier 1 (default: 1000000.0)
- `TIER2`: Available funds for tier 2 (default: 2000000.0)
- `TIER3`: Available funds for tier 3 (default: 500000.0)

### Calculated Market Values
- `TIER1_MV`: Sum of (amount * price_per_unit) for tier 1 assets
- `TIER2_MV`: Sum of (amount * price_per_unit) for tier 2 assets
- `TIER3_MV`: Sum of (amount * price_per_unit) for tier 3 assets

### Service Configuration
- `ASSETS_DB_URI`: PostgreSQL connection string
- `PORT`: Service port (default: 8080)
- `REQUEST_TIMEOUT`: HTTP request timeout (default: 30)

## Database Integration

### Assets Database (assets-db)
- **Reads**: Asset information by ID
- **Updates**: Asset amounts and timestamps
- **Creates**: New assets for first-time purchases

### Database Operations
```sql
-- Get asset by ID
SELECT asset_id, tier_number, asset_name, amount, price_per_unit, last_updated
FROM assets WHERE asset_id = %s

-- Create new asset
INSERT INTO assets (asset_id, tier_number, asset_name, amount, price_per_unit, last_updated)
VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)

-- Update asset amount
UPDATE assets 
SET amount = %s, last_updated = CURRENT_TIMESTAMP
WHERE asset_id = %s
```

## Execution Probability Algorithm

The service uses a realistic probability calculation for order execution:

1. **Price Factor**: Based on price difference between request and market
2. **Volume Factor**: Based on volume ratio between request and available
3. **Liquidity Factor**: Random market condition simulation
4. **Combined Probability**: Weighted combination of all factors

This ensures realistic market behavior where orders are more likely to execute when:
- Prices are close to market value
- Volumes are reasonable
- Market conditions are favorable

## Error Handling

### Common Error Scenarios
- **insufficient_funds**: Not enough pool funds for BUY orders
- **insufficient_assets**: Not enough assets for SELL orders
- **asset_not_found**: Asset doesn't exist for SELL orders
- **order_rejected**: Order rejected due to market conditions
- **database_error**: Database operation failures

### HTTP Status Codes
- **200**: Order executed successfully
- **400**: Order failed (business logic error)
- **500**: Service error (system failure)

## Integration Points

### Dependencies
- **assets-db**: Primary database for asset inventory
- **PostgreSQL**: Database driver (psycopg2)

### Service Communication
- **Input**: Order requests from trading services
- **Output**: Order execution results and status updates
- **Database**: Real-time inventory updates

## Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export TIER1=1000000
export TIER2=2000000
export TIER3=500000

# Run locally
python execute_order_svc.py
```

### Docker
```bash
# Build image
docker build -t execute-order-svc .

# Run container
docker run -p 8080:8080 \
  -e TIER1=1000000 \
  -e TIER2=2000000 \
  -e TIER3=500000 \
  execute-order-svc
```

### Kubernetes
```bash
# Deploy with Skaffold
skaffold dev
```

## Testing

The service includes comprehensive testing covering:
- Order execution logic
- Database operations
- Error handling scenarios
- Probability calculations

Run tests:
```bash
python -m pytest tests/
```

## Performance Considerations

### Optimization Features
- Efficient database queries with proper indexing
- Real-time tier value calculations
- Optimized probability algorithms
- Connection pooling for database operations

### Scalability
- Stateless service design
- Horizontal scaling support
- Database connection management
- Asynchronous processing capabilities
