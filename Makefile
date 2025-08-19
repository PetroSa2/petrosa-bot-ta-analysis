#!/usr/bin/env make

.PHONY: help setup lint test security build container deploy pipeline clean format install-dev install-prod

# Default target
help:
	@echo "Petrosa Data Extractor - Available Commands"
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
	@echo "Docker:"
	@echo "  build          Build Docker image"
	@echo "  container      Test Docker container"
	@echo "  docker-clean   Clean up Docker images"
	@echo ""
	@echo "Deployment:"
	@echo "  deploy         Deploy to Kubernetes cluster"
	@echo "  pipeline       Run complete local CI/CD pipeline"
	@echo ""
	@echo "Utilities:"
	@echo "  clean          Clean up temporary files and caches"
	@echo "  run            Run the application locally"
	@echo "  run-docker     Run the application in Docker"
	@echo ""
	@echo "Bug Investigation:"
	@echo "  bug-confirm    Confirm bug behavior locally"
	@echo "  bug-investigate Investigate root cause"
	@echo "  bug-test       Test bug fixes"
	@echo "  bug-all        Run complete bug investigation"
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
	black tradeengine/ tests/

test:
	@echo "🧪 Running tests..."
	@chmod +x scripts/local-pipeline.sh
	@./scripts/local-pipeline.sh test

security:
	@echo "🔒 Running security scan..."
	@chmod +x scripts/local-pipeline.sh
	@./scripts/local-pipeline.sh security

# Docker
build:
	@echo "🐳 Building Docker image..."
	@chmod +x scripts/local-pipeline.sh
	@./scripts/local-pipeline.sh build

container:
	@echo "📦 Testing Docker container..."
	@chmod +x scripts/local-pipeline.sh
	@./scripts/local-pipeline.sh container

docker-clean:
	@echo "🧹 Cleaning up Docker images..."
	docker rmi yurisa2/petrosa-tradeengine:latest 2>/dev/null || true
	docker rmi yurisa2/petrosa-tradeengine:local-* 2>/dev/null || true
	docker rmi yurisa2/petrosa-tradeengine:v* 2>/dev/null || true
	docker system prune -f

# Deployment
deploy:
	@echo "☸️  Deploying to Kubernetes..."
	@chmod +x scripts/local-pipeline.sh
	@./scripts/local-pipeline.sh deploy

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
	kubectl get pods -n petrosa-apps -l app=petrosa-tradeengine
	kubectl get svc -n petrosa-apps -l app=petrosa-tradeengine
	kubectl get ingress -n petrosa-apps -l app=petrosa-tradeengine

k8s-logs:
	@echo "📋 Kubernetes logs:"
	kubectl logs -n petrosa-apps -l app=petrosa-tradeengine --tail=50

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

# Database utilities
db-migrate:
	@echo "🗄️  Running database migrations..."
	@echo "Trading Engine uses MongoDB - migrations handled automatically"

db-seed:
	@echo "🌱 Seeding database with initial data..."
	@echo "Trading Engine initializes with default configuration"

# Monitoring
monitor:
	@echo "📊 Trading Engine metrics:"
	@echo "Check logs for order execution and signal processing metrics"

# Backup
backup:
	@echo "💾 Trading Engine backup:"
	@echo "Backup MongoDB collections and configuration"

# Restore
restore:
	@echo "🔄 Trading Engine restore:"
	@echo "Restore from MongoDB backup and configuration"

# Bug Investigation
bug-confirm:
	@echo "🔍 Confirming bug behavior locally..."
	@chmod +x scripts/bug-investigation.sh
	@./scripts/bug-investigation.sh confirm

bug-investigate:
	@echo "🔬 Investigating root cause..."
	@chmod +x scripts/bug-investigation.sh
	@./scripts/bug-investigation.sh investigate

bug-test:
	@echo "🧪 Testing bug fixes..."
	@chmod +x scripts/bug-investigation.sh
	@./scripts/bug-investigation.sh test

bug-all:
	@echo "🚨 Running complete bug investigation..."
	@chmod +x scripts/bug-investigation.sh
	@./scripts/bug-investigation.sh all 