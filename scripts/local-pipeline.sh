#!/bin/bash

# Petrosa TA Bot Local Pipeline Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to run a stage
run_stage() {
    local stage=$1
    print_status "Running stage: $stage"
    
    case $stage in
        "setup")
            print_status "Setting up development environment..."
            ./scripts/dev-setup.sh
            print_success "Setup completed"
            ;;
        "lint")
            print_status "Running linting checks..."
            black --check ta_bot/ tests/
            flake8 ta_bot/ tests/
            mypy ta_bot/
            ruff check ta_bot/ tests/
            print_success "Linting completed"
            ;;
        "test")
            print_status "Running tests..."
            python -m pytest tests/ --cov=ta_bot --cov-report=html --cov-report=term
            print_success "Tests completed"
            ;;
        "security")
            print_status "Running security scans..."
            bandit -r ta_bot/
            safety check
            print_success "Security scans completed"
            ;;
        "build")
            print_status "Building Docker image..."
            docker build -t yurisa2/petrosa-ta-bot:latest .
            print_success "Docker build completed"
            ;;
        "container")
            print_status "Testing Docker container..."
            docker run --rm yurisa2/petrosa-ta-bot:latest python -c "import ta_bot; print('TA Bot imported successfully')"
            print_success "Container test completed"
            ;;
        "deploy")
            print_status "Deploying to Kubernetes..."
            export KUBECONFIG=k8s/kubeconfig.yaml
            kubectl apply -f k8s/
            print_success "Deployment completed"
            ;;
        *)
            print_error "Unknown stage: $stage"
            exit 1
            ;;
    esac
}

# Main execution
if [ $# -eq 0 ]; then
    print_error "Usage: $0 <stage> [stage2] [stage3] ..."
    echo "Available stages: setup, lint, test, security, build, container, deploy"
    echo "Use 'all' to run all stages"
    exit 1
fi

# Check if running all stages
if [ "$1" = "all" ]; then
    stages=("setup" "lint" "test" "security" "build" "container" "deploy")
else
    stages=("$@")
fi

# Run each stage
for stage in "${stages[@]}"; do
    if run_stage "$stage"; then
        print_success "Stage '$stage' completed successfully"
    else
        print_error "Stage '$stage' failed"
        exit 1
    fi
done

print_success "All stages completed successfully!" 