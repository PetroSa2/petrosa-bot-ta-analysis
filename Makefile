#!/usr/bin/env make

.PHONY: help setup lint test security build container deploy pipeline clean format install-dev install-prod

# Default target
help:
	@echo "Petrosa TA Bot - Available Commands"
	@echo "==================================="
	@echo ""
	@echo "Development Setup:"
	@echo "  setup          Setup Python environment and install dependencies"
	@echo "  install-dev    Install development dependencies"
	@echo "  install-prod   Install production dependencies"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint           Run all linting and formatting checks"
	@echo "  format         Format code with black"
	@echo "  test           Run tests with coverage"
	@echo "  security       Run security scan with Trivy"
	@echo ""
	@echo "Version Management:"
	@echo "  version        Generate patch version"
	@echo "  version-local  Generate local development version"
	@echo ""
	@echo "Docker:"
	@echo "  build          Build Docker image with local version"
	@echo "  build-patch    Build Docker image with patch version"
	@echo "  container      Test Docker container"
	@echo "  docker-clean   Clean up Docker images"
	@echo ""
	@echo "Deployment:"
	@echo "  deploy         Deploy to Kubernetes with local version"
	@echo "  deploy-patch   Deploy to Kubernetes with patch version"
	@echo "  deploy-full    Run full deployment pipeline with versioning"
	@echo "  pipeline       Run complete local CI/CD pipeline"
	@echo ""
	@echo "Utilities:"
	@echo "  clean          Clean up temporary files and caches"
	@echo "  run            Run the application locally"
	@echo "  run-docker     Run the application in Docker"
	@echo ""

# Development setup
setup:
	@echo "🚀 Setting up development environment..."
	@chmod +x scripts/dev-setup.sh
	@./scripts/dev-setup.sh

install-dev:
	@echo "📚 Installing development dependencies..."
	pip install -r requirements-dev.txt

install-prod:
	@echo "📦 Installing production dependencies..."
	pip install -r requirements.txt

# Code quality
lint:
	@echo "🔍 Running linting checks..."
	@chmod +x scripts/local-pipeline.sh
	@./scripts/local-pipeline.sh lint

format:
	@echo "🎨 Formatting code with black..."
	black ta_bot/ tests/

test:
	@echo "🧪 Running tests..."
	@chmod +x scripts/local-pipeline.sh
	@./scripts/local-pipeline.sh test

security:
	@echo "🔒 Running security scan..."
	@chmod +x scripts/local-pipeline.sh
	@./scripts/local-pipeline.sh security

# Version Management
version:
	@echo "🏷️  Generating version..."
	@chmod +x scripts/version-manager.sh
	@./scripts/version-manager.sh generate patch

version-local:
	@echo "🏷️  Generating local version..."
	@chmod +x scripts/version-manager.sh
	@./scripts/version-manager.sh generate local

# Docker
build:
	@echo "🐳 Building Docker image with version..."
	@chmod +x scripts/version-manager.sh
	@./scripts/version-manager.sh build local

build-patch:
	@echo "🐳 Building Docker image with patch version..."
	@chmod +x scripts/version-manager.sh
	@./scripts/version-manager.sh build patch

container:
	@echo "📦 Testing Docker container..."
	@chmod +x scripts/local-pipeline.sh
	@./scripts/local-pipeline.sh container

docker-clean:
	@echo "🧹 Cleaning up Docker images..."
	docker rmi yurisa2/petrosa-ta-bot:latest 2>/dev/null || true
	docker rmi yurisa2/petrosa-ta-bot:local-* 2>/dev/null || true
	docker rmi yurisa2/petrosa-ta-bot:v* 2>/dev/null || true
	docker system prune -f

# Deployment
deploy:
	@echo "☸️  Deploying to Kubernetes with version..."
	@chmod +x scripts/version-manager.sh
	@./scripts/version-manager.sh deploy local

deploy-patch:
	@echo "☸️  Deploying to Kubernetes with patch version..."
	@chmod +x scripts/version-manager.sh
	@./scripts/version-manager.sh deploy patch

deploy-full:
	@echo "🚀 Running full deployment pipeline..."
	@chmod +x scripts/version-manager.sh
	@./scripts/version-manager.sh full patch false

pipeline:
	@echo "🔄 Running complete local CI/CD pipeline..."
	@chmod +x scripts/local-pipeline.sh
	@./scripts/local-pipeline.sh all

# Application
run:
	@echo "🏃 Running TA Bot locally..."
	python -m ta_bot.main

run-docker:
	@echo "🐳 Running TA Bot in Docker..."
	docker run -p 8000:8000 petrosa/ta-bot:latest

# Utilities
clean:
	@echo "🧹 Cleaning up..."
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .trivy/
	rm -f k8s/deployment-local.yaml
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

# Quick development workflow
dev: setup lint test
	@echo "✅ Development workflow completed!"

# Quick production check
prod: lint test security build container
	@echo "✅ Production readiness check completed!"

# Install additional tools (optional)
install-tools:
	@echo "🔧 Installing additional development tools..."
	@if command -v brew >/dev/null 2>&1; then \
		echo "Installing tools via Homebrew..."; \
		brew install trivy jq; \
	elif command -v apt-get >/dev/null 2>&1; then \
		echo "Installing tools via apt..."; \
		sudo apt-get update && sudo apt-get install -y trivy jq; \
	elif command -v yum >/dev/null 2>&1; then \
		echo "Installing tools via yum..."; \
		sudo yum install -y trivy jq; \
	else \
		echo "Please install trivy and jq manually"; \
	fi

# Kubernetes utilities
k8s-status:
	@echo "📊 Kubernetes deployment status:"
	kubectl get pods -n petrosa-apps -l app=petrosa-ta-bot
	kubectl get svc -n petrosa-apps -l app=petrosa-ta-bot
	kubectl get ingress -n petrosa-apps -l app=petrosa-ta-bot

k8s-logs:
	@echo "📋 Kubernetes logs:"
	kubectl logs -n petrosa-apps -l app=petrosa-ta-bot --tail=50

k8s-clean:
	@echo "🧹 Cleaning up Kubernetes resources..."
	kubectl delete namespace petrosa-apps 2>/dev/null || true

# Health checks
health:
	@echo "🏥 Testing health endpoints..."
	@curl -s http://localhost:8000/health | jq . || echo "Health endpoint not available"
	@curl -s http://localhost:8000/ready | jq . || echo "Ready endpoint not available"
	@curl -s http://localhost:8000/live | jq . || echo "Live endpoint not available"

# Documentation
docs:
	@echo "📚 Documentation available in README.md"
	@echo "API documentation: Check the signal output format in README"

# Performance testing
benchmark:
	@echo "⚡ Running performance tests..."
	python -m pytest tests/ -v

# Database utilities (not applicable for TA Bot)
db-migrate:
	@echo "🗄️  TA Bot doesn't use a database"

db-seed:
	@echo "🌱 TA Bot doesn't use a database"

# Monitoring
monitor:
	@echo "📊 TA Bot metrics:"
	@echo "Check logs for signal generation metrics"

# Backup
backup:
	@echo "💾 TA Bot doesn't require backup"

# Restore
restore:
	@echo "🔄 TA Bot doesn't require restore" 