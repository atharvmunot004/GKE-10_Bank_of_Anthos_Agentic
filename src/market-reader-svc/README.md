# Market Reader Service (market-reader-svc)

The market reader service provides real-time market data simulation and analytics for investment assets in the Bank of Anthos portfolio management system.

## Overview

The service simulates market data for different asset types and provides comprehensive analytics suitable for AI agents to manage portfolios effectively.

## Supported Asset Types

- **CRYPTO**: Cryptocurrencies (Tier 1) - High volatility simulation
- **ETF**: Exchange-Traded Funds (Tier 2) - Moderate volatility simulation  
- **MUTUAL-FUND**: Mutual Funds (Tier 2) - Low volatility simulation
- **EQUITY**: Individual Stocks (Tier 2) - Moderate volatility simulation

## API Endpoints

### Health & Readiness
- `GET /health` - Service health check
- `GET /ready` - Service readiness check

### Market Data Operations
- `POST /api/v1/market-data` - Get market data for specific asset type
- `GET /api/v1/market-summary` - Get overall market summary

## Market Data Request

### Request Format
```json
{
  "type": "CRYPTO"
}
```

### Response Format
```json
{
  "status": "success",
  "asset_type": "CRYPTO",
  "timestamp": "2024-01-01T10:00:00Z",
  "assets": [
    {
      "asset_id": 1,
      "asset_name": "BTC",
      "tier_number": 1,
      "amount": 1000.0,
      "price_per_unit": 50000.0,
      "market_value": 50000000.0,
      "price_change_percent": 2.5,
      "last_updated": "2024-01-01T10:00:00Z"
    }
  ],
  "analytics": {
    "market_type": "CRYPTO",
    "timestamp": "2024-01-01T10:00:00Z",
    "total_assets": 2,
    "price_summary": {
      "min_price": 3000.0,
      "max_price": 50000.0,
      "avg_price": 26500.0,
      "total_market_value": 65000000.0
    },
    "volatility_analysis": {
      "high_volatility_assets": [...],
      "stable_assets": [...],
      "recommended_for_short_term": [...],
      "recommended_for_long_term": [...]
    },
    "portfolio_recommendations": {
      "diversification_score": 0.8,
      "risk_level": "high",
      "suggested_allocation": {
        "BTC": "5-15%",
        "ETH": "5-15%"
      }
    }
  }
}
```

## Integration

### Dependencies
- **assets-db**: PostgreSQL database for asset information
- **yfinance**: Optional real market data integration

### Database Operations
- Reads asset information from assets-db
- Updates asset prices with simulated market data
- Maintains price history and analytics

## Market Simulation

### Volatility Models
- **Cryptocurrencies**: 5% daily volatility
- **ETFs**: 2% daily volatility
- **Mutual Funds**: 1.5% daily volatility
- **Equities**: 3% daily volatility

### Price Updates
- Simulates realistic price movements
- Updates assets-db with new prices
- Calculates price change percentages
- Tracks market value changes

## AI Agent Analytics

### Portfolio Recommendations
- **Diversification Score**: Based on number of assets
- **Risk Level**: Calculated from asset types and volatility
- **Suggested Allocation**: Percentage recommendations per asset

### Market Analysis
- **Price Summary**: Min, max, average prices and total market value
- **Volatility Analysis**: Categorizes assets by risk level
- **Investment Recommendations**: Short-term vs long-term suggestions

## Environment Variables

- `ASSETS_DB_URI`: PostgreSQL connection string
- `PORT`: Service port (default: 8080)
- `REQUEST_TIMEOUT`: HTTP request timeout (default: 30)

## Database Schema Integration

### Assets Table Updates
```sql
UPDATE assets 
SET price_per_unit = %s, last_updated = CURRENT_TIMESTAMP
WHERE asset_id = %s
```

### Asset Queries
```sql
SELECT asset_id, tier_number, asset_name, amount, price_per_unit, last_updated
FROM assets 
WHERE tier_number = %s
```

## Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python market_reader_svc.py
```

### Docker
```bash
# Build image
docker build -t market-reader-svc .

# Run container
docker run -p 8080:8080 market-reader-svc
```

### Kubernetes
```bash
# Deploy with Skaffold
skaffold dev
```

## Testing

The service includes comprehensive testing covering:
- Market data simulation accuracy
- Database integration
- Analytics generation
- Error handling scenarios

Run tests:
```bash
python -m pytest tests/
```

## Performance Considerations

### Optimization Features
- Efficient database queries with proper indexing
- Cached market data where appropriate
- Optimized simulation algorithms
- Real-time price updates

### Scalability
- Stateless service design
- Horizontal scaling support
- Database connection pooling
- Asynchronous processing capabilities
