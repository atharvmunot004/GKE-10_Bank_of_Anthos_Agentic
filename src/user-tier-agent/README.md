# User Tier Agent

AI-powered financial tier allocation agent using Google Gemini LLM for intelligent investment and withdrawal allocation.

## Overview

The User Tier Agent is a microservice that analyzes user transaction history and intelligently allocates investment or withdrawal amounts into three financial tiers:

- **Tier 1**: Highly liquid, instant access for emergencies
- **Tier 2**: Moderately liquid, 15-day access for planned expenses  
- **Tier 3**: Long-term investments, compound growth over years

## Architecture

- **Framework**: FastAPI with Python 3.9+
- **LLM**: Google Gemini (gemini-1.5-pro) via LangChain
- **Orchestration**: LangChain AgentExecutor
- **Deployment**: Kubernetes with Docker containers

## Features

- AI-powered transaction history analysis
- Intelligent tier allocation based on spending patterns
- Fallback to default allocation for new users
- Comprehensive error handling and validation
- Health checks and monitoring
- Load balancing and auto-scaling
- Security with network policies

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Kubernetes cluster (for deployment)
- kubectl configured
- Google Gemini API key

### Local Development

1. **Clone and setup**:
   ```bash
   cd src/user-tier-agent
   make dev-setup
   ```

2. **Configure environment**:
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

3. **Start services**:
   ```bash
   make dev-start
   ```

4. **Access the API**:
   - API: http://localhost:8080
   - Health: http://localhost:8080/health
   - Docs: http://localhost:8080/docs

### Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f user-tier-agent

# Stop services
docker-compose down
```

## API Endpoints

### POST /api/v1/allocation/allocate-tiers

Allocate tiers for investment or withdrawal request.

**Request**:
```json
{
  "uuid": "123e4567-e89b-12d3-a456-426614174000",
  "accountid": "account-123",
  "amount": 10000.0,
  "purpose": "INVEST"
}
```

**Response**:
```json
{
  "success": true,
  "allocation": {
    "tier1": 1000.0,
    "tier2": 2000.0,
    "tier3": 7000.0
  },
  "reasoning": "AI-powered allocation based on transaction history",
  "request_id": "req-123"
}
```

### GET /api/v1/allocation/allocate-tiers/{accountid}/default

Get default tier allocation for a given amount.

**Parameters**:
- `accountid`: Account identifier
- `amount`: Amount to allocate

### GET /health

Health check endpoint.

### GET /ready

Readiness check endpoint.

### GET /metrics

Prometheus metrics endpoint.

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key (from GOOGLE_API_KEY env var) | Required |
| `LEDGER_DB_URL` | Ledger database URL | `http://ledger-db:8080` |
| `QUEUE_DB_URL` | Queue database URL | `http://queue-db:8080` |
| `PORTFOLIO_DB_URL` | Portfolio database URL | `http://portfolio-db:8080` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `DEFAULT_TIER1_PERCENTAGE` | Default Tier 1 percentage | `20` |
| `DEFAULT_TIER2_PERCENTAGE` | Default Tier 2 percentage | `30` |
| `DEFAULT_TIER3_PERCENTAGE` | Default Tier 3 percentage | `50` |

## Testing

### Run All Tests
```bash
make test-all
```

### Unit Tests
```bash
make test-unit
```

### Integration Tests
```bash
make test-integration
```

### End-to-End Tests
```bash
make test-e2e
```

### Load Tests
```bash
make test-load
```

### Prompt Tests
```bash
make test-prompt
```

### Coverage Report
```bash
make test-coverage
```

## Deployment

### Kubernetes Deployment

1. **Build and deploy**:
   ```bash
   ./deploy.sh deploy
   ```

2. **Check status**:
   ```bash
   ./deploy.sh status
   ```

3. **Undeploy**:
   ```bash
   ./deploy.sh undeploy
   ```

### Manual Deployment

1. **Build image**:
   ```bash
   make build
   ```

2. **Push to registry**:
   ```bash
   make push
   ```

3. **Deploy to Kubernetes**:
   ```bash
   make deploy
   ```

## Monitoring

### Health Checks

- **Liveness**: `/health` - Service is running
- **Readiness**: `/ready` - Service is ready to accept requests

### Metrics

- **Business metrics**: Allocation requests, success rates
- **Technical metrics**: HTTP requests, response times, LLM token usage
- **System metrics**: CPU, memory, pod status

### Logging

- **Structured logging**: JSON format with request IDs
- **Log levels**: DEBUG, INFO, WARN, ERROR
- **Context**: Request ID, account ID, operation type

## Security

- **Network policies**: Restrict ingress/egress traffic
- **Service accounts**: Minimal permissions
- **Secrets management**: Kubernetes secrets for API keys
- **Input validation**: Request sanitization and validation
- **Rate limiting**: Per-account request limits

## Performance

### Scaling

- **Horizontal Pod Autoscaler**: CPU and memory based scaling
- **Resource limits**: CPU 500m, Memory 512Mi
- **Replicas**: 2-10 pods based on load

### Optimization

- **Caching**: Redis for transaction history and user profiles
- **Connection pooling**: HTTP client connection reuse
- **Async processing**: Concurrent tool execution

## Troubleshooting

### Common Issues

1. **Service not starting**:
   ```bash
   kubectl logs -l app=user-tier-agent
   ```

2. **Health check failing**:
   ```bash
   kubectl describe pod -l app=user-tier-agent
   ```

3. **External service connection issues**:
   ```bash
   kubectl exec -it <pod-name> -- curl http://ledger-db:8080/health
   ```

### Debug Mode

Enable debug logging:
```bash
kubectl set env deployment/user-tier-agent LOG_LEVEL=DEBUG
```

## Development

### Code Quality

```bash
# Format code
make format

# Run linting
make lint

# Type checking
mypy app/
```

### Adding New Features

1. Create feature branch
2. Implement with tests
3. Update documentation
4. Submit pull request

### Project Structure

```
src/user-tier-agent/
├── app/                    # Application code
│   ├── api/               # API endpoints
│   ├── core/              # Core functionality
│   ├── models/            # Data models
│   └── services/          # Business logic
├── tests/                 # Test suites
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   ├── e2e/               # End-to-end tests
│   ├── load/              # Load tests
│   └── prompt/            # Prompt tests
├── kubernetes-manifests/  # K8s deployment files
├── docker-compose.yml     # Local development
├── Dockerfile             # Container image
├── requirements.txt       # Dependencies
└── Makefile              # Development commands
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

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
