# Petrosa TA Bot

A Kubernetes-based Technical Analysis bot for cryptocurrency trading with comprehensive CI/CD pipeline and local development capabilities.

## 🚀 Quick Start

```bash
# Complete setup
make setup

# Run local pipeline
make pipeline

# Deploy to Kubernetes
make deploy

# Check deployment status
make k8s-status
```

## 📋 Prerequisites

- **Python 3.11+**: Required for development and runtime
- **Docker**: Required for containerization and local testing
- **kubectl**: Required for Kubernetes deployment (remote cluster)
- **Make**: Required for using the Makefile commands

**Note**: This project uses a **remote MicroK8s cluster** - no local Kubernetes installation required.

## 🏗️ Architecture

### Core Components
- **Signal Engine**: Coordinates all trading strategies
- **Strategies**: 5 technical analysis strategies implemented
- **NATS Listener**: Subscribes to candle updates
- **REST Publisher**: Sends signals to external API

### Trading Strategies
1. **Momentum Pulse**: MACD histogram crossovers
2. **Band Fade Reversal**: Bollinger Band mean reversion
3. **Golden Trend Sync**: EMA pullback entries
4. **Range Break Pop**: Volatility breakouts
5. **Divergence Trap**: Hidden bullish divergence

## 📊 Signal Format

```json
{
  "symbol": "BTCUSDT",
  "period": "15m",
  "signal": "BUY",
  "confidence": 0.74,
  "strategy": "momentum_pulse",
  "metadata": {
    "rsi": 58.3,
    "macd_hist": 0.0012,
    "adx": 27
  }
}
```

## 🛠️ Development

### Setup
```bash
# Complete environment setup
make setup

# Install development dependencies
make install-dev
```

### Code Quality
```bash
# Run all linting
make lint

# Format code
make format

# Run tests
make test

# Security scan
make security
```

### Docker Operations
```bash
# Build image
make build

# Test container
make container

# Run in Docker
make run-docker
```

## ☸️ Kubernetes Deployment

### Remote Cluster Setup
- **Cluster Type**: Remote MicroK8s (no local installation required)
- **Connection**: Use `k8s/kubeconfig.yaml` for cluster access
- **Server**: Remote MicroK8s cluster at `https://192.168.194.253:16443`

### Namespace
- **Name**: `petrosa-apps`
- **Labels**: `app=petrosa-ta-bot`

### Components
- **Deployment**: 3 replicas with health checks
- **Service**: ClusterIP on port 80
- **Ingress**: SSL-enabled with Let's Encrypt
- **HPA**: Auto-scaling based on CPU/memory

### Deployment Commands
```bash
# Set kubeconfig for remote cluster
export KUBECONFIG=k8s/kubeconfig.yaml

# Deploy to remote cluster
make deploy

# Check status
make k8s-status

# View logs
make k8s-logs

# Clean up
make k8s-clean
```

## 🔧 Environment Variables

### Required for Production
- `NATS_URL`: NATS server URL
- `API_ENDPOINT`: REST API endpoint for signals
- `LOG_LEVEL`: Logging level (default: INFO)
- `ENVIRONMENT`: Environment name (default: production)

### Optional Configuration
- `SUPPORTED_SYMBOLS`: Comma-separated list of trading pairs
- `SUPPORTED_TIMEFRAMES`: Comma-separated list of timeframes
- `DEBUG`: Enable debug mode (default: false)
- `SIMULATION_MODE`: Enable simulation mode (default: false)

## 🧪 Testing

### Run Tests
```bash
# Run all tests
make test

# Run specific test file
python -m pytest tests/test_signal_engine.py -v

# Run with coverage
python -m pytest tests/ --cov=ta_bot --cov-report=html
```

### Test Structure
```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── test_signal_engine.py    # Signal engine tests
└── test_strategies.py       # Strategy tests
```

## 🔒 Security

### Security Scanning
```bash
# Run security scans
make security

# Bandit (Python security linter)
bandit -r ta_bot/

# Safety (dependency vulnerability checker)
safety check
```

### Container Security
```bash
# Trivy vulnerability scanner
trivy image petrosa/ta-bot:latest
```

## 📈 Monitoring

### Health Checks
- `/health` - Detailed health status
- `/ready` - Readiness probe
- `/live` - Liveness probe

### Metrics
- Signal generation rate
- Strategy performance metrics
- Error rates and latency

## 🚀 CI/CD Pipeline

### GitHub Actions
- **Lint**: Code quality checks (black, flake8, mypy, ruff)
- **Test**: Unit tests with coverage
- **Security**: Vulnerability scanning with Trivy
- **Build**: Docker image building
- **Deploy**: Kubernetes deployment

### Local Pipeline
```bash
# Run complete pipeline
./scripts/local-pipeline.sh all

# Run specific stages
./scripts/local-pipeline.sh lint test
./scripts/local-pipeline.sh build container
./scripts/local-pipeline.sh deploy
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Python Environment Issues
```bash
# Check Python version
python3 --version

# Recreate virtual environment
rm -rf .venv
make setup
```

#### 2. Docker Build Issues
```bash
# Clean Docker cache
make docker-clean

# Rebuild image
make build
```

#### 3. Kubernetes Connection Issues
```bash
# Set kubeconfig for remote cluster
export KUBECONFIG=k8s/kubeconfig.yaml

# Check cluster connection
kubectl --kubeconfig=k8s/kubeconfig.yaml cluster-info

# Check namespace
kubectl --kubeconfig=k8s/kubeconfig.yaml get namespace petrosa-apps
```

#### 4. NumPy Compatibility Issues
```bash
# Fix NumPy 2.x compatibility issues
pip install 'numpy<2.0.0'

# Reinstall dependencies
pip install -r requirements.txt
```

## 📚 Documentation

- **API Documentation**: Check the signal output format above
- **Strategy Details**: See individual strategy implementations in `ta_bot/strategies/`
- **Configuration**: Environment variables and Kubernetes configs
- **Deployment**: Kubernetes manifests and deployment guides

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `make test`
5. Run linting: `make lint`
6. Submit a pull request

## 📄 License

This project is part of the Petrosa trading ecosystem.

## 🔗 Related Projects

- **petrosa-tradeengine**: Main trading engine
- **petrosa-api**: REST API service
- **petrosa-dashboard**: Web dashboard

---

**Note**: This is a production-ready TA bot with comprehensive CI/CD pipeline and **remote MicroK8s cluster** deployment - no local Kubernetes installation required. 