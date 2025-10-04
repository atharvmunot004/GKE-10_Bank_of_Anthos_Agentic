# User Tier Agent Makefile

# Variables
IMAGE_NAME = user-tier-agent
VERSION = v1.0.0
REGISTRY = localhost:5000
FULL_IMAGE_NAME = $(REGISTRY)/$(IMAGE_NAME):$(VERSION)

# Docker commands
.PHONY: build
build:
	docker build -t $(FULL_IMAGE_NAME) .

.PHONY: push
push:
	docker push $(FULL_IMAGE_NAME)

.PHONY: run
run:
	docker run -p 8080:8080 --env-file .env $(FULL_IMAGE_NAME)

.PHONY: run-local
run-local:
	python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload

# Development commands
.PHONY: install
install:
	pip install -r requirements.txt

.PHONY: install-dev
install-dev:
	pip install -r requirements.txt
	pip install pytest pytest-asyncio pytest-cov black flake8 mypy

.PHONY: format
format:
	black .
	isort .

.PHONY: lint
lint:
	flake8 .
	mypy .

.PHONY: test
test:
	pytest tests/ -v

.PHONY: test-unit
test-unit:
	pytest tests/unit/ -v

.PHONY: test-integration
test-integration:
	pytest tests/integration/ -v

.PHONY: test-e2e
test-e2e:
	pytest tests/e2e/ -v

.PHONY: test-prompt
test-prompt:
	pytest tests/prompt/ -v

.PHONY: test-coverage
test-coverage:
	pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

.PHONY: test-load
test-load:
	cd tests/load && python run_load_tests.py --test normal --users 50 --duration 5m

.PHONY: test-all
test-all: test-unit test-integration test-e2e test-prompt

# Docker Compose commands
.PHONY: up
up:
	docker-compose up -d

.PHONY: down
down:
	docker-compose down

.PHONY: logs
logs:
	docker-compose logs -f user-tier-agent

.PHONY: restart
restart:
	docker-compose restart user-tier-agent

# Kubernetes commands
.PHONY: deploy
deploy:
	kubectl apply -f ../../kubernetes-manifests/user-tier-agent.yaml

.PHONY: undeploy
undeploy:
	kubectl delete -f ../../kubernetes-manifests/user-tier-agent.yaml

.PHONY: status
status:
	kubectl get pods -l app=user-tier-agent
	kubectl get svc -l app=user-tier-agent

.PHONY: logs-k8s
logs-k8s:
	kubectl logs -l app=user-tier-agent -f

# Health check commands
.PHONY: health
health:
	curl -f http://localhost:8080/health || echo "Service is not healthy"

.PHONY: ready
ready:
	curl -f http://localhost:8080/ready || echo "Service is not ready"

.PHONY: metrics
metrics:
	curl http://localhost:8080/metrics

# Cleanup commands
.PHONY: clean
clean:
	docker system prune -f
	docker volume prune -f

.PHONY: clean-all
clean-all:
	docker system prune -a -f
	docker volume prune -f

# Development workflow
.PHONY: dev-setup
dev-setup: install-dev
	cp env.example .env
	@echo "Please update .env with your configuration"

.PHONY: dev-start
dev-start: up
	@echo "Services started. Access the API at http://localhost:8080"
	@echo "Health check: http://localhost:8080/health"
	@echo "API docs: http://localhost:8080/docs"

.PHONY: dev-stop
dev-stop: down

.PHONY: dev-test
dev-test: test-all test-load

# CI/CD commands
.PHONY: ci-build
ci-build: build test-all

.PHONY: ci-deploy
ci-deploy: push deploy

.PHONY: ci-test
ci-test: test-coverage test-load

# Help
.PHONY: help
help:
	@echo "Available commands:"
	@echo "  build          - Build Docker image"
	@echo "  push           - Push Docker image to registry"
	@echo "  run            - Run Docker container"
	@echo "  run-local      - Run locally with uvicorn"
	@echo "  install        - Install dependencies"
	@echo "  install-dev    - Install development dependencies"
	@echo "  format         - Format code with black and isort"
	@echo "  lint           - Run linting checks"
	@echo "  test           - Run all tests"
	@echo "  test-unit      - Run unit tests"
	@echo "  test-integration - Run integration tests"
	@echo "  test-e2e       - Run end-to-end tests"
	@echo "  test-prompt    - Run prompt tests"
	@echo "  test-coverage  - Run tests with coverage"
	@echo "  test-load      - Run load tests"
	@echo "  up             - Start services with docker-compose"
	@echo "  down           - Stop services"
	@echo "  logs           - Show service logs"
	@echo "  deploy         - Deploy to Kubernetes"
	@echo "  undeploy       - Remove from Kubernetes"
	@echo "  status         - Show Kubernetes status"
	@echo "  health         - Check service health"
	@echo "  ready          - Check service readiness"
	@echo "  metrics        - Show service metrics"
	@echo "  clean          - Clean Docker system"
	@echo "  dev-setup      - Setup development environment"
	@echo "  dev-start      - Start development environment"
	@echo "  dev-stop       - Stop development environment"
	@echo "  dev-test       - Run all development tests"
