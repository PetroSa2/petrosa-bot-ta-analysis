# Petrosa ta-analysis Makefile

PYTHON := python3
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest
IMAGE_NAME := petrosa-bot-ta-analysis
NAMESPACE := petrosa

.PHONY: help setup install-dev lint format type-check test test-coverage test-quality security build container deploy k8s-status k8s-logs k8s-clean pipeline clean

help: ## Show this help message
	@echo "🚀 Petrosa $(IMAGE_NAME) - Standard Development Commands"
	@echo "========================================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Complete environment setup
	@echo "🚀 Setting up development environment..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt
	@echo "✅ Setup completed!"

install-dev: ## Install development dependencies
	$(PIP) install -r requirements-dev.txt

lint: ## Run all linters (ruff, black, flake8)
	@echo "🔍 Running linters..."
	ruff check .
	black --check .
	flake8 .

format: ## Format code with black and ruff
	@echo "🎨 Formatting code..."
	black .
	ruff check . --fix

type-check: ## Run static type checking with mypy
	@echo "🧪 Running type checks..."
	mypy ta_bot/

test: ## Run unit tests
	@echo "🧪 Running tests..."
	$(PYTEST) tests/unit/

test-coverage: ## Run tests with coverage reporting
	@echo "📊 Running tests with coverage..."
	$(PYTEST) --cov=ta_bot --cov-report=term-missing --cov-report=xml tests/

test-quality: ## Run test quality check (assertions check)
	@echo "🔍 Checking test quality..."
	python3 scripts/check-test-assertions.py $(shell find tests -name "test_*.py")

security: ## Run security scans (gitleaks, bandit, trivy)
	@echo "🔐 Running security scans..."
	@echo "1️⃣ Gitleaks (Local check)..."
	@if command -v gitleaks >/dev/null 2>&1; then \
		gitleaks detect --verbose; \
	else \
		echo "⚠️  Gitleaks not installed. Skipping local check."; \
	fi
	@echo ""
	@echo "2️⃣ detect-secrets..."
	@if command -v detect-secrets >/dev/null 2>&1; then \
		detect-secrets scan --baseline .secrets.baseline || echo "⚠️  New secrets detected"; \
	else \
		echo "⚠️  detect-secrets not installed."; \
	fi
	@echo ""
	@echo "3️⃣ Bandit (Python Security)..."
	@bandit -r . -f json -o bandit-report.json || true
	@if [ -f bandit-report.json ]; then \
		echo "📊 Bandit found issues. Check bandit-report.json"; \
		python -m json.tool bandit-report.json | grep -A 5 '"issue_severity"' | head -20 || true; \
	fi
	@echo ""
	@echo "4️⃣ Trivy (Vulnerability Scanner)..."
	@if command -v trivy >/dev/null 2>&1; then \
		trivy fs . --severity HIGH,CRITICAL --format table; \
	else \
		echo "⚠️  Trivy not installed."; \
	fi

clean: ## Clean up temporary files
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage coverage.xml htmlcov/ bandit-report.json

pipeline: ## Run complete CI pipeline locally
	@echo "🔄 Running local pipeline..."
	$(MAKE) lint
	$(MAKE) type-check
	$(MAKE) test-coverage
	$(MAKE) test-quality
	$(MAKE) security
	@echo "✅ Pipeline completed!"
