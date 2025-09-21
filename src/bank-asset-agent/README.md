# Bank Asset Agent Service

The `bank-asset-agent` service provides AI-powered asset management, market analysis, and investment decision-making capabilities for the Bank of Anthos application.

## Features

- **Real-time Market Data Integration**: Connects to market-reader-svc for live market data
- **Intelligent Asset Management**: AI-powered analysis and recommendations for investment assets
- **Rule-based Decision Making**: Integrates with rule-checker-svc for compliance and risk management
- **Order Execution**: Coordinates with execute-order-svc for trade execution
- **Queue Management**: Processes requests from user-request-queue-svc
- **Asset Database Integration**: Manages asset data through assets-db

## Service Dependencies

The Bank Asset Agent communicates with the following services:

1. **market-reader-svc**: Real-time market data and pricing information
2. **rule-checker-svc**: Business rule validation and compliance checking
3. **execute-order-svc**: Investment order execution and management
4. **assets-db**: Asset information storage and retrieval
5. **user-request-queue-svc**: Investment and withdrawal request processing

## Available Tools

1. **get_market_data**: Retrieve real-time market data from market-reader-svc
2. **analyze_asset_performance**: Analyze asset performance and trends
3. **check_investment_rules**: Validate investment rules and compliance
4. **execute_investment_order**: Execute investment orders through execute-order-svc
5. **manage_asset_queue**: Process requests from user-request-queue-svc
6. **update_asset_data**: Update asset information in assets-db

## Environment Variables

- `VERSION`: Service version
- `PORT`: Service port (default: 8080)
- `ENABLE_TRACING`: Enable OpenTelemetry tracing
- `ENABLE_METRICS`: Enable metrics collection
- `MARKET_READER_URL`: URL for market-reader-svc
- `RULE_CHECKER_URL`: URL for rule-checker-svc
- `EXECUTE_ORDER_URL`: URL for execute-order-svc
- `ASSETS_DB_URI`: Database connection URI for assets-db
- `QUEUE_SVC_URL`: URL for user-request-queue-svc

## API

The service exposes a gRPC API with the following methods:

- `AnalyzeMarketData`: Analyze market data and provide insights
- `ProcessInvestmentRequest`: Process investment requests from the queue
- `ExecuteAssetManagement`: Execute asset management operations
- `ValidateInvestmentRules`: Validate investment rules and compliance

## Security

- JWT-based authentication for all operations
- Secure communication with all dependent services
- Risk scoring and compliance validation
- Audit logging for all asset management operations

## Deployment

The service is deployed using Skaffold with Kubernetes manifests:

```bash
# Deploy in development
skaffold dev --profile development

# Deploy specific service
skaffold dev --module bank-asset-agent
```

## Directory Structure

```
src/bank-asset-agent/
├── agents/           # AI agent implementations
├── api/             # API definitions and handlers
├── utils/           # Utility functions and helpers
├── k8s/             # Kubernetes manifests
├── tests/           # Test suites
├── Dockerfile       # Container definition
├── requirements.txt # Python dependencies
├── skaffold.yaml    # Skaffold configuration
└── llm.txt         # LLM documentation
```