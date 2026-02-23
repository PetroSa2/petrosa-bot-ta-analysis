# Configuration Guide

Complete guide for configuring the Petrosa TA Bot across all environments.

## 🔧 Environment Variables

### Required Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `NATS_URL` | NATS server connection URL | - | `nats://localhost:4222` |
| `API_ENDPOINT` | REST API endpoint for signals | - | `http://localhost:8080/signals` |
| `LOG_LEVEL` | Logging level | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `ENVIRONMENT` | Environment name | `production` | `development`, `staging`, `production` |

### Optional Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `SUPPORTED_SYMBOLS` | Comma-separated trading pairs | `BTCUSDT,ETHUSDT` | `BTCUSDT,ETHUSDT,ADAUSDT` |
| `SUPPORTED_TIMEFRAMES` | Comma-separated timeframes | `15m,1h` | `5m,15m,1h,4h` |
| `DEBUG` | Enable debug mode | `false` | `true`, `false` |
| `SIMULATION_MODE` | Enable simulation mode | `false` | `true`, `false` |

### Technical Analysis Configuration

| Variable | Description | Default | Range |
|----------|-------------|---------|-------|
| `RSI_PERIOD` | RSI calculation period | `14` | `5-50` |
| `MACD_FAST` | MACD fast period | `12` | `5-50` |
| `MACD_SLOW` | MACD slow period | `26` | `10-100` |
| `MACD_SIGNAL` | MACD signal period | `9` | `5-20` |
| `ADX_PERIOD` | ADX calculation period | `14` | `5-50` |
| `BB_PERIOD` | Bollinger Bands period | `20` | `10-50` |
| `BB_STD` | Bollinger Bands standard deviation | `2.0` | `1.0-3.0` |
| `ATR_PERIOD` | ATR calculation period | `14` | `5-50` |

### Health Check Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `HEALTH_CHECK_PORT` | Health check port | `8000` | `8080` |
| `HEALTH_CHECK_INTERVAL` | Health check interval (seconds) | `30` | `15`, `60` |

## 📁 Configuration Files

### Environment File (`.env`)

```bash
# Copy template
cp env.example .env

# Edit configuration
nano .env
```

**Example `.env` file**:
```bash
# NATS Configuration
NATS_URL=nats://localhost:4222

# API Configuration
API_ENDPOINT=http://localhost:8080/signals

# Logging
LOG_LEVEL=INFO
ENVIRONMENT=development

# Trading Configuration
SUPPORTED_SYMBOLS=BTCUSDT,ETHUSDT,ADAUSDT
SUPPORTED_TIMEFRAMES=15m,1h

# Technical Analysis Configuration
RSI_PERIOD=14
MACD_FAST=12
MACD_SLOW=26
MACD_SIGNAL=9
ADX_PERIOD=14
BB_PERIOD=20
BB_STD=2.0
ATR_PERIOD=14

# Health Check Configuration
HEALTH_CHECK_PORT=8000
HEALTH_CHECK_INTERVAL=30

# Development
DEBUG=false
SIMULATION_MODE=false
```

### Kubernetes ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ta-bot-config
  namespace: petrosa-apps
data:
  nats_url: "nats://nats-server:4222"
  api_endpoint: "http://api-server:8080/signals"
  log_level: "INFO"
  environment: "production"
  supported_symbols: "BTCUSDT,ETHUSDT,ADAUSDT"
  supported_timeframes: "15m,1h"
  rsi_period: "14"
  macd_fast: "12"
  macd_slow: "26"
  macd_signal: "9"
  adx_period: "14"
  bb_period: "20"
  bb_std: "2.0"
  atr_period: "14"
```

### Kubernetes Secrets

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: ta-bot-secrets
  namespace: petrosa-apps
type: Opaque
data:
  nats_username: ""  # Base64 encoded
  nats_password: ""  # Base64 encoded
  api_auth_token: "" # Base64 encoded
```

## 🏗️ Environment-Specific Configuration

### Development Environment

```bash
# Development settings
ENVIRONMENT=development
LOG_LEVEL=DEBUG
DEBUG=true
SIMULATION_MODE=true

# Local services
NATS_URL=nats://localhost:4222
API_ENDPOINT=http://localhost:8080/signals

# Limited symbols for testing
SUPPORTED_SYMBOLS=BTCUSDT
SUPPORTED_TIMEFRAMES=15m
```

### Staging Environment

```bash
# Staging settings
ENVIRONMENT=staging
LOG_LEVEL=INFO
DEBUG=false
SIMULATION_MODE=true

# Staging services
NATS_URL=nats://staging-nats:4222
API_ENDPOINT=http://staging-api:8080/signals

# Full symbol set
SUPPORTED_SYMBOLS=BTCUSDT,ETHUSDT,ADAUSDT
SUPPORTED_TIMEFRAMES=15m,1h
```

### Production Environment

```bash
# Production settings
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=false
SIMULATION_MODE=false

# Production services
NATS_URL=nats://prod-nats:4222
API_ENDPOINT=http://prod-api:8080/signals

# Full configuration
SUPPORTED_SYMBOLS=BTCUSDT,ETHUSDT,ADAUSDT,SOLUSDT
SUPPORTED_TIMEFRAMES=15m,1h,4h
```

## 🔧 Configuration Management

### Environment Variable Loading

The TA Bot uses Python's `os` module and `python-dotenv` for configuration:

```python
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get configuration
NATS_URL = os.getenv('NATS_URL', 'nats://localhost:4222')
API_ENDPOINT = os.getenv('API_ENDPOINT', 'http://localhost:8080/signals')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')
```

### Configuration Validation

```python
def validate_config():
    """Validate required configuration."""
    required_vars = ['NATS_URL', 'API_ENDPOINT']

    for var in required_vars:
        if not os.getenv(var):
            raise ValueError(f"Required environment variable {var} not set")

    # Validate NATS URL format
    nats_url = os.getenv('NATS_URL')
    if not nats_url.startswith(('nats://', 'tls://')):
        raise ValueError("NATS_URL must start with nats:// or tls://")

    # Validate log level
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
    if log_level not in valid_levels:
        raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
```

### Dynamic Configuration

```python
class Config:
    """Configuration management class."""

    def __init__(self):
        self.nats_url = os.getenv('NATS_URL')
        self.api_endpoint = os.getenv('API_ENDPOINT')
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.environment = os.getenv('ENVIRONMENT', 'production')

        # Parse supported symbols
        symbols_str = os.getenv('SUPPORTED_SYMBOLS', 'BTCUSDT,ETHUSDT')
        self.supported_symbols = [s.strip() for s in symbols_str.split(',')]

        # Parse supported timeframes
        timeframes_str = os.getenv('SUPPORTED_TIMEFRAMES', '15m,1h')
        self.supported_timeframes = [t.strip() for t in timeframes_str.split(',')]

        # Technical analysis settings
        self.rsi_period = int(os.getenv('RSI_PERIOD', '14'))
        self.macd_fast = int(os.getenv('MACD_FAST', '12'))
        self.macd_slow = int(os.getenv('MACD_SLOW', '26'))
        self.macd_signal = int(os.getenv('MACD_SIGNAL', '9'))
        self.adx_period = int(os.getenv('ADX_PERIOD', '14'))
        self.bb_period = int(os.getenv('BB_PERIOD', '20'))
        self.bb_std = float(os.getenv('BB_STD', '2.0'))
        self.atr_period = int(os.getenv('ATR_PERIOD', '14'))
```

## 🔄 Configuration Updates

### Hot Reload Configuration

```python
import signal
import threading

class ConfigManager:
    """Manages configuration with hot reload capability."""

    def __init__(self):
        self.config = Config()
        self._reload_event = threading.Event()

        # Setup signal handler for config reload
        signal.signal(signal.SIGUSR1, self._reload_config)

    def _reload_config(self, signum, frame):
        """Reload configuration on signal."""
        self.config = Config()
        self._reload_event.set()
        logger.info("Configuration reloaded")

    def wait_for_reload(self, timeout=None):
        """Wait for configuration reload."""
        return self._reload_event.wait(timeout)
```

### Kubernetes ConfigMap Updates

```bash
# Update ConfigMap
kubectl apply -f k8s/configmap.yaml

# Restart deployment to pick up changes
kubectl rollout restart deployment petrosa-ta-bot -n petrosa-apps

# Check rollout status
kubectl rollout status deployment petrosa-ta-bot -n petrosa-apps
```

### Environment Variable Updates

```bash
# Update environment variables in deployment
kubectl set env deployment/petrosa-ta-bot \
  LOG_LEVEL=DEBUG \
  SUPPORTED_SYMBOLS="BTCUSDT,ETHUSDT" \
  -n petrosa-apps

# Restart deployment
kubectl rollout restart deployment petrosa-ta-bot -n petrosa-apps
```

## 🔒 Security Configuration

### Sensitive Data Management

#### Kubernetes Secrets
```bash
# Create secrets
kubectl create secret generic ta-bot-secrets \
  --from-literal=nats-username="your-username" \
  --from-literal=nats-password="your-password" \
  --from-literal=api-auth-token="your-token" \
  -n petrosa-apps

# Update secrets
kubectl patch secret ta-bot-secrets \
  -p '{"data":{"nats-password":"'$(echo -n "new-password" | base64)'"}}' \
  -n petrosa-apps
```

#### Environment Variable Security
```bash
# Never log sensitive data
export NATS_PASSWORD="secret-password"
export API_AUTH_TOKEN="secret-token"

# Use environment-specific files
cp env.example .env.development
cp env.example .env.staging
cp env.example .env.production
```

### Network Security

#### NATS TLS Configuration
```bash
# TLS-enabled NATS connection
NATS_URL=tls://nats-server:4222

# With authentication
NATS_URL=tls://username:password@nats-server:4222
```

#### API Security
```bash
# HTTPS API endpoint
API_ENDPOINT=https://api-server:8443/signals

# With authentication header
API_AUTH_HEADER=Authorization: Bearer your-token
```

## 📊 Configuration Monitoring

### Configuration Health Checks

```python
def check_config_health():
    """Check configuration health."""
    health_status = {
        'nats_connection': check_nats_connection(),
        'api_connection': check_api_connection(),
        'symbols_configured': len(config.supported_symbols) > 0,
        'timeframes_configured': len(config.supported_timeframes) > 0
    }

    return health_status
```

### Configuration Metrics

```python
# Prometheus metrics for configuration
from prometheus_client import Gauge

config_symbols_gauge = Gauge('ta_bot_supported_symbols', 'Number of supported symbols')
config_timeframes_gauge = Gauge('ta_bot_supported_timeframes', 'Number of supported timeframes')

# Update metrics
config_symbols_gauge.set(len(config.supported_symbols))
config_timeframes_gauge.set(len(config.supported_timeframes))
```

## 🧪 Configuration Testing

### Configuration Validation Tests

```python
def test_config_validation():
    """Test configuration validation."""
    # Test required variables
    with pytest.raises(ValueError):
        validate_config()  # Missing required vars

    # Test NATS URL format
    os.environ['NATS_URL'] = 'invalid-url'
    with pytest.raises(ValueError):
        validate_config()

    # Test log level
    os.environ['LOG_LEVEL'] = 'INVALID'
    with pytest.raises(ValueError):
        validate_config()
```

### Environment-Specific Tests

```python
def test_development_config():
    """Test development configuration."""
    os.environ['ENVIRONMENT'] = 'development'
    os.environ['DEBUG'] = 'true'

    config = Config()
    assert config.environment == 'development'
    assert config.debug is True
```

## 📋 Configuration Checklist

### Pre-Deployment Checklist
- [ ] **Environment Variables**: All required variables set
- [ ] **NATS Configuration**: Server URL and credentials configured
- [ ] **API Configuration**: Endpoint URL and authentication set
- [ ] **Trading Symbols**: Supported symbols configured
- [ ] **Timeframes**: Supported timeframes configured
- [ ] **Technical Analysis**: Indicator parameters set
- [ ] **Security**: Secrets and TLS configured
- [ ] **Logging**: Log level and format configured

### Runtime Configuration
- [ ] **Hot Reload**: Configuration reload mechanism tested
- [ ] **Validation**: Configuration validation working
- [ ] **Monitoring**: Configuration metrics available
- [ ] **Backup**: Configuration backup procedures in place

---

**Next Steps**:
- Read [Deployment Guide](./DEPLOYMENT.md) for production deployment
- Check [Security Guide](./SECURITY.md) for security best practices
- Review [Troubleshooting](./TROUBLESHOOTING.md) for common issues
