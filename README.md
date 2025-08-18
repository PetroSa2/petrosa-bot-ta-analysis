# Petrosa TA Bot

A Kubernetes-based Technical Analysis bot for cryptocurrency trading with comprehensive CI/CD pipeline and local development capabilities. **Now fully integrated with Petrosa Trade Engine for end-to-end automated trading.**

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
- **Signal Engine**: Coordinates all trading strategies and generates unified signals
- **Strategies**: 5 technical analysis strategies implemented
- **NATS Listener**: Subscribes to candle updates from Data Extractor
- **Signal Publisher**: Sends signals to Trade Engine via NATS and REST API
- **MySQL Client**: Persists signals and fetches historical candle data

### Trading Strategies
1. **Momentum Pulse**: MACD histogram crossovers
2. **Band Fade Reversal**: Bollinger Band mean reversion
3. **Golden Trend Sync**: EMA pullback entries
4. **Range Break Pop**: Volatility breakouts
5. **Divergence Trap**: Hidden bullish divergence

### End-to-End Trading Flow
```
Data Extractor → MySQL → TA Bot → Trade Engine → Binance
     ↓              ↓         ↓           ↓         ↓
  Klines Data   Candle DB  Signals   Order Exec   Live Trades
```

## 📊 Signal Format (Unified with Trade Engine)

The TA Bot now generates signals in the exact format expected by the Trade Engine:

```json
{
  "strategy_id": "momentum_pulse_15m",
  "symbol": "BTCUSDT",
  "action": "buy",
  "confidence": 0.74,
  "current_price": 50000.0,
  "price": 50000.0,
  "strategy_mode": "deterministic",
  "strength": "medium",
  "quantity": 0.0,
  "source": "ta_bot",
  "strategy": "momentum_pulse",
  "metadata": {
    "rsi": 58.3,
    "macd_hist": 0.0012,
    "adx": 27
  },
  "timeframe": "15m",
  "order_type": "market",
  "time_in_force": "GTC",
  "position_size_pct": 0.1,
  "stop_loss": 49000.0,
  "take_profit": 51000.0,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Key Signal Features
- **Price Data**: Includes `current_price` and `price` for accurate trade execution
- **Risk Management**: Automatic `stop_loss` and `take_profit` calculation using ATR
- **Position Sizing**: Configurable `position_size_pct` for risk control
- **Strategy Metadata**: Rich technical indicator data for analysis
- **Unified Format**: Direct compatibility with Trade Engine - no adapters needed

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

### Signal Testing
```bash
# Test signal format and Trade Engine compatibility
python test_signal_format.py

# Test complete signal flow with sample data
python test_signal_flow.py
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
- `NATS_URL`: NATS server URL (from `petrosa-common-config`)
- `API_ENDPOINT`: REST API endpoint for signals (`http://petrosa-tradeengine-service/trade/signal`)
- `LOG_LEVEL`: Logging level (default: INFO)
- `ENVIRONMENT`: Environment name (default: production)
- `NATS_ENABLED`: Enable NATS messaging (default: true)

### Optional Configuration
- `SUPPORTED_SYMBOLS`: Comma-separated list of trading pairs (default: BTCUSDT,ETHUSDT,ADAUSDT)
- `SUPPORTED_TIMEFRAMES`: Comma-separated list of timeframes (default: 15m,1h)
- `MYSQL_URI`: MySQL connection string (from `petrosa-sensitive-credentials`)
- `MYSQL_DATABASE`: MySQL database name (default: petrosa)

### Kubernetes Configuration
The TA Bot uses these Kubernetes resources:
- **ConfigMap**: `ta-bot-config` - Strategy and API settings
- **ConfigMap**: `petrosa-common-config` - NATS and environment settings
- **Secret**: `petrosa-sensitive-credentials` - MySQL connection string

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

### Signal Integration Tests
```bash
# Test signal format compatibility
python test_signal_format.py

# Test complete signal flow
python test_signal_flow.py
```

### Test Structure
```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── test_signal_engine.py    # Signal engine tests
└── test_strategies.py       # Strategy tests

# Signal integration tests
test_signal_format.py        # Signal format validation
test_signal_flow.py          # End-to-end signal flow
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
- `/ready` - Readiness probe for Kubernetes
- `/live` - Liveness probe for Kubernetes

### Metrics
- Signal generation rate
- Strategy performance metrics
- Error rates and latency
- NATS message processing rate

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

#### 4. Signal Integration Issues
```bash
# Test signal format locally
python test_signal_format.py

# Check NATS connectivity
kubectl --kubeconfig=k8s/kubeconfig.yaml logs -l app=petrosa-ta-bot | grep NATS

# Check Trade Engine connectivity
kubectl --kubeconfig=k8s/kubeconfig.yaml logs -l app=petrosa-tradeengine | grep signal
```

#### 5. NumPy Compatibility Issues
```bash
# Fix NumPy 2.x compatibility issues
pip install 'numpy<2.0.0'

# Reinstall dependencies
pip install -r requirements.txt
```

## 🚀 End-to-End Trading Setup

### Prerequisites for Live Trading
1. **Data Extractor**: Must be writing klines to MySQL
2. **NATS Server**: Running and accessible
3. **Trade Engine**: Configured with valid Binance API credentials
4. **MySQL Database**: Accessible with proper schema

### Deployment Checklist
```bash
# 1. Verify all services are running
kubectl --kubeconfig=k8s/kubeconfig.yaml get pods -n petrosa-apps

# 2. Check NATS connectivity
kubectl --kubeconfig=k8s/kubeconfig.yaml logs -l app=petrosa-ta-bot | grep "Connected to NATS"

# 3. Verify signal generation
kubectl --kubeconfig=k8s/kubeconfig.yaml logs -l app=petrosa-ta-bot | grep "Generated.*signals"

# 4. Check Trade Engine signal processing
kubectl --kubeconfig=k8s/kubeconfig.yaml logs -l app=petrosa-tradeengine | grep "Processing signal"
```

### Live Trading Configuration
To enable live trading (not simulation):
1. Set `SIMULATION_ENABLED=false` in Trade Engine
2. Set `BINANCE_TESTNET=false` for live trading (or `true` for testnet)
3. Ensure valid `BINANCE_API_KEY` and `BINANCE_API_SECRET` in `petrosa-sensitive-credentials`

## 📚 Documentation

- **API Documentation**: See signal format above
- **Strategy Details**: See individual strategy implementations in `ta_bot/strategies/`
- **Configuration**: Environment variables and Kubernetes configs
- **Deployment**: Kubernetes manifests and deployment guides
- **Integration**: End-to-end trading flow documentation

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

- **petrosa-tradeengine**: Main trading engine (now fully integrated)
- **petrosa-binance-data-extractor**: Data extraction service
- **petrosa-api**: REST API service
- **petrosa-dashboard**: Web dashboard

---

**Note**: This is a production-ready TA bot with comprehensive CI/CD pipeline, **remote MicroK8s cluster** deployment, and **full integration with Petrosa Trade Engine for end-to-end automated trading**. 