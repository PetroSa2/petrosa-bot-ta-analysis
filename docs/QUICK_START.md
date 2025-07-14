# Quick Start Guide

Get the Petrosa TA Bot up and running in minutes.

## 🚀 Prerequisites

Before you begin, ensure you have:

- **Python 3.11+** installed
- **Docker** installed (for containerized deployment)
- **kubectl** installed (for Kubernetes deployment)
- **Make** installed (for automation)

## ⚡ Quick Start (5 minutes)

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/petrosa/ta-bot.git
cd ta-bot

# Complete setup
make setup
```

### 2. Configure Environment

```bash
# Copy environment template
cp env.example .env

# Edit configuration (optional)
nano .env
```

### 3. Run Locally

```bash
# Start the TA Bot locally
make run

# Or run in Docker
make run-docker
```

### 4. Test the Setup

```bash
# Run tests
make test

# Check health endpoints
make health
```

## 🐳 Docker Quick Start

### Build and Run Container

```bash
# Build Docker image
make build

# Run container
docker run -p 8000:8000 petrosa/ta-bot:latest
```

### Test Container

```bash
# Test container functionality
make container
```

## ☸️ Kubernetes Quick Start

### Deploy to Remote Cluster

```bash
# Set kubeconfig for remote MicroK8s cluster
export KUBECONFIG=k8s/kubeconfig.yaml

# Deploy to production
make deploy

# Check deployment status
make k8s-status
```

### Verify Deployment

```bash
# View pods
kubectl get pods -n petrosa-apps -l app=petrosa-ta-bot

# View services
kubectl get svc -n petrosa-apps -l app=petrosa-ta-bot

# View logs
make k8s-logs
```

## 🔧 Development Quick Start

### Local Development

```bash
# Install development dependencies
make install-dev

# Run linting
make lint

# Run tests with coverage
make test

# Format code
make format
```

### Complete Pipeline

```bash
# Run complete local CI/CD pipeline
make pipeline

# Or run specific stages
./scripts/local-pipeline.sh lint test build
```

## 📊 Verify Everything Works

### Health Checks

```bash
# Test health endpoints
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/live
```

### Signal Generation

The TA Bot will automatically:
1. Connect to NATS server
2. Listen for candle updates
3. Generate trading signals
4. Send signals via REST API

### Monitor Logs

```bash
# View application logs
docker logs <container_id>

# Or for Kubernetes
kubectl logs -n petrosa-apps -l app=petrosa-ta-bot
```

## 🎯 Next Steps

### For Development
1. Read [Development Guide](./DEVELOPMENT.md)
2. Review [Testing Guide](./TESTING.md)
3. Check [Architecture Overview](./ARCHITECTURE.md)

### For Production
1. Follow [Deployment Guide](./DEPLOYMENT.md)
2. Configure [Security](./SECURITY.md)
3. Set up [Monitoring](./MONITORING.md)

### For Trading
1. Review [Trading Strategies](./STRATEGIES.md)
2. Configure [Signal Engine](./SIGNAL_ENGINE.md)
3. Check [API Reference](./API_REFERENCE.md)

## 🚨 Troubleshooting

### Common Issues

#### Python Environment Issues
```bash
# Check Python version
python3 --version

# Recreate virtual environment
rm -rf .venv
make setup
```

#### Docker Issues
```bash
# Clean Docker cache
make docker-clean

# Rebuild image
make build
```

#### Kubernetes Issues
```bash
# Check cluster connection
kubectl --kubeconfig=k8s/kubeconfig.yaml cluster-info

# Check namespace
kubectl --kubeconfig=k8s/kubeconfig.yaml get namespace petrosa-apps
```

### Get Help

- Check [Troubleshooting Guide](./TROUBLESHOOTING.md)
- Review [Configuration](./CONFIGURATION.md)
- Check logs: `make k8s-logs`

## 📋 Quick Reference

### Essential Commands

```bash
# Setup
make setup                    # Complete environment setup
make install-dev             # Install development dependencies

# Development
make lint                    # Run linting
make test                    # Run tests
make format                  # Format code
make security                # Security scan

# Docker
make build                   # Build Docker image
make container               # Test container
make run-docker             # Run in Docker

# Kubernetes
make deploy                  # Deploy to K8s
make k8s-status             # Check deployment status
make k8s-logs               # View logs
make k8s-clean              # Clean up resources

# Application
make run                     # Run locally
make health                  # Test health endpoints
make pipeline                # Run complete pipeline
```

### Environment Variables

```bash
# Required
NATS_URL=nats://localhost:4222
API_ENDPOINT=http://localhost:8080/signals

# Optional
LOG_LEVEL=INFO
ENVIRONMENT=development
SUPPORTED_SYMBOLS=BTCUSDT,ETHUSDT
SUPPORTED_TIMEFRAMES=15m,1h
```

---

**🎉 Congratulations!** You've successfully set up the Petrosa TA Bot. 

For detailed information, check the [full documentation](./README.md). 