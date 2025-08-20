# Development Guide

Complete guide for developing the Petrosa TA Bot.

## 🚀 Development Setup

### Prerequisites

- **Python 3.11+**: Required for development
- **Git**: Version control
- **Docker**: Container testing
- **Make**: Automation commands
- **IDE**: VS Code, PyCharm, or similar

### Initial Setup

```bash
# Clone repository
git clone https://github.com/petrosa/ta-bot.git
cd ta-bot

# Setup development environment
make setup

# Install development dependencies
make install-dev
```

## 🏗️ Project Structure

```
petrosa-ta-bot/
├── ta_bot/                    # Main application code
│   ├── __init__.py
│   ├── main.py               # Application entry point
│   ├── config.py             # Configuration management
│   ├── health.py             # Health check endpoints
│   ├── core/                 # Core engine components
│   │   ├── signal_engine.py  # Signal generation engine
│   │   ├── indicators.py     # Technical indicators
│   │   └── confidence.py     # Confidence calculation
│   ├── strategies/           # Trading strategies
│   │   ├── base_strategy.py  # Base strategy class
│   │   ├── momentum_pulse.py
│   │   ├── band_fade_reversal.py
│   │   ├── golden_trend_sync.py
│   │   ├── range_break_pop.py
│   │   └── divergence_trap.py
│   ├── services/             # External services
│   │   ├── nats_listener.py  # NATS message handling
│   │   └── publisher.py      # Signal publishing
│   └── models/               # Data models
│       └── signal.py         # Signal data model
├── tests/                    # Test suite
│   ├── __init__.py
│   ├── conftest.py          # Test configuration
│   ├── test_signal_engine.py
│   └── test_strategies.py
├── k8s/                     # Kubernetes manifests
├── scripts/                 # Automation scripts
├── docs/                    # Documentation
├── requirements.txt         # Production dependencies
├── requirements-dev.txt     # Development dependencies
├── Makefile                # Build automation
└── Dockerfile              # Container definition
```

## 🔧 Development Workflow

### 1. Code Quality

```bash
# Run all linting checks
make lint

# Format code
make format

# Run type checking
mypy ta_bot/

# Run security scans
make security
```

### 2. Testing

```bash
# Run all tests
make test

# Run specific test file
python -m pytest tests/test_signal_engine.py -v

# Run with coverage
python -m pytest tests/ --cov=ta_bot --cov-report=html

# Run integration tests
python -m pytest tests/ -m integration
```

### 3. Local Development

```bash
# Run application locally
make run

# Run in Docker
make run-docker

# Test health endpoints
make health
```

### 4. Complete Pipeline

```bash
# Run complete local CI/CD pipeline
make pipeline

# Or run specific stages
./scripts/local-pipeline.sh lint test build
```

## 📝 Coding Standards

### Python Style Guide

Follow **PEP 8** and use **Black** for formatting:

```python
# Good
def calculate_rsi(data: pd.DataFrame, period: int = 14) -> float:
    """Calculate RSI indicator."""
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]


# Bad
def calculate_rsi(data,period=14):
    delta=data['close'].diff()
    gain=(delta.where(delta>0,0)).rolling(window=period).mean()
    loss=(-delta.where(delta<0,0)).rolling(window=period).mean()
    rs=gain/loss
    rsi=100-(100/(1+rs))
    return rsi.iloc[-1]
```

### Type Hints

Always use type hints for function parameters and return values:

```python
from typing import Dict, List, Optional, Any
import pandas as pd

def analyze_market_data(
    candle_data: pd.DataFrame,
    indicators: Dict[str, float]
) -> Optional[Signal]:
    """Analyze market data and return signal if conditions are met."""
    pass
```

### Docstrings

Use Google-style docstrings:

```python
def calculate_macd(data: pd.DataFrame) -> Dict[str, float]:
    """Calculate MACD indicator.

    Args:
        data: DataFrame with OHLCV data

    Returns:
        Dictionary containing MACD, signal, and histogram values

    Raises:
        ValueError: If data is empty or missing required columns
    """
    pass
```

### Error Handling

Use proper exception handling:

```python
import logging

logger = logging.getLogger(__name__)

def safe_calculate_indicator(data: pd.DataFrame) -> float:
    """Safely calculate indicator with error handling."""
    try:
        return calculate_rsi(data)
    except KeyError as e:
        logger.error(f"Missing required column: {e}")
        raise ValueError(f"Data missing required column: {e}")
    except Exception as e:
        logger.error(f"Indicator calculation failed: {e}")
        raise
```

## 🧪 Testing Guidelines

### Test Structure

```python
# tests/test_signal_engine.py
import pytest
from ta_bot.core.signal_engine import SignalEngine

class TestSignalEngine:
    """Test cases for SignalEngine."""

    @pytest.fixture
    def signal_engine(self):
        """Create SignalEngine instance for testing."""
        return SignalEngine()

    def test_initialization(self, signal_engine):
        """Test SignalEngine initialization."""
        assert len(signal_engine.strategies) == 5
        assert signal_engine.indicators is not None

    def test_signal_generation(self, signal_engine):
        """Test signal generation."""
        # Test implementation
        pass
```

### Test Categories

1. **Unit Tests**: Test individual functions and classes
2. **Integration Tests**: Test component interactions
3. **End-to-End Tests**: Test complete workflows

### Test Data

```python
# tests/conftest.py
import pytest
import pandas as pd

@pytest.fixture
def sample_candle_data():
    """Create sample candle data for testing."""
    return pd.DataFrame({
        'open': [50000, 50050, 50100],
        'high': [50100, 50150, 50200],
        'low': [49900, 49950, 50000],
        'close': [50050, 50100, 50150],
        'volume': [1000, 1100, 1200]
    })

@pytest.fixture
def sample_indicators():
    """Create sample indicators for testing."""
    return {
        'rsi': 58.3,
        'macd_hist': 0.0012,
        'adx': 27.5
    }
```

## 🔍 Debugging

### Local Debugging

```python
# Add debug logging
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_function():
    logger.debug("Entering function")
    # Your code here
    logger.debug("Exiting function")
```

### Docker Debugging

```bash
# Run container with debug mode
docker run -e DEBUG=true -p 8000:8000 petrosa/ta-bot:latest

# Access container shell
docker run -it petrosa/ta-bot:latest /bin/bash
```

### Kubernetes Debugging

```bash
# View pod logs
kubectl logs -n petrosa-apps -l app=petrosa-ta-bot

# Access pod shell
kubectl exec -it -n petrosa-apps <pod-name> -- /bin/bash

# Port forward for local access
kubectl port-forward -n petrosa-apps svc/petrosa-ta-bot-service 8000:80
```

## 🚀 Adding New Features

### 1. Create Feature Branch

```bash
git checkout -b feature/new-strategy
```

### 2. Implement Feature

```python
# ta_bot/strategies/new_strategy.py
from typing import Optional, Dict
import pandas as pd
from .base_strategy import BaseStrategy
from ..models.signal import Signal

class NewStrategy(BaseStrategy):
    """New trading strategy implementation."""

    def get_name(self) -> str:
        return "new_strategy"

    def analyze(
        self,
        candle_data: pd.DataFrame,
        indicators: Dict[str, float]
    ) -> Optional[Signal]:
        """Analyze market data and return signal."""
        # Implementation here
        pass
```

### 3. Add Tests

```python
# tests/test_new_strategy.py
import pytest
from ta_bot.strategies.new_strategy import NewStrategy

class TestNewStrategy:
    """Test cases for NewStrategy."""

    def test_strategy_initialization(self):
        """Test strategy initialization."""
        strategy = NewStrategy()
        assert strategy.get_name() == "new_strategy"

    def test_signal_generation(self):
        """Test signal generation."""
        # Test implementation
        pass
```

### 4. Update Documentation

```markdown
# docs/STRATEGIES.md
## New Strategy

Description of the new strategy...

### Configuration
- Parameter 1: Description
- Parameter 2: Description

### Signal Conditions
- Condition 1: Description
- Condition 2: Description
```

### 5. Run Quality Checks

```bash
# Run all checks
make lint
make test
make security

# Run complete pipeline
make pipeline
```

## 🔧 Configuration Management

### Environment Variables

```bash
# Development configuration
TA_BOT_LOG_LEVEL=DEBUG
TA_BOT_ENVIRONMENT=development
TA_BOT_SUPPORTED_SYMBOLS=BTCUSDT,ETHUSDT
TA_BOT_SUPPORTED_TIMEFRAMES=15m,1h

# Testing configuration
TA_BOT_SIMULATION_MODE=true
TA_BOT_TEST_MODE=true
```

### Configuration Class

```python
# ta_bot/config.py
from pydantic import BaseSettings, Field

class Config(BaseSettings):
    """Application configuration."""

    # Core settings
    nats_url: str = Field(default="nats://localhost:4222")
    api_endpoint: str = Field(default="http://localhost:8080/signals")
    log_level: str = Field(default="INFO")
    environment: str = Field(default="production")

    # Trading settings
    supported_symbols: str = Field(default="BTCUSDT,ETHUSDT,ADAUSDT")
    supported_timeframes: str = Field(default="15m,1h")

    # Technical analysis settings
    rsi_period: int = Field(default=14)
    macd_fast: int = Field(default=12)
    macd_slow: int = Field(default=26)
    macd_signal: int = Field(default=9)

    class Config:
        env_prefix = "TA_BOT_"
```

## 📊 Performance Optimization

### Profiling

```python
import cProfile
import pstats

def profile_function():
    """Profile function performance."""
    profiler = cProfile.Profile()
    profiler.enable()

    # Your code here
    signal_engine.process_candle(candle_data)

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)
```

### Memory Optimization

```python
# Use generators for large datasets
def process_candles(candles):
    """Process candles using generator."""
    for candle in candles:
        yield process_single_candle(candle)

# Use context managers for resources
from contextlib import contextmanager

@contextmanager
def managed_connection():
    """Manage database connection."""
    conn = create_connection()
    try:
        yield conn
    finally:
        conn.close()
```

## 🔒 Security Best Practices

### Input Validation

```python
from pydantic import BaseModel, validator

class CandleData(BaseModel):
    """Validate candle data input."""

    symbol: str
    period: str
    open: float
    high: float
    low: float
    close: float
    volume: float

    @validator('symbol')
    def validate_symbol(cls, v):
        if not v.isalnum():
            raise ValueError('Symbol must be alphanumeric')
        return v.upper()

    @validator('period')
    def validate_period(cls, v):
        valid_periods = ['1m', '5m', '15m', '1h', '4h', '1d']
        if v not in valid_periods:
            raise ValueError(f'Period must be one of {valid_periods}')
        return v
```

### Secure Configuration

```python
# Never hardcode secrets
import os

# Good
api_key = os.getenv('API_KEY')

# Bad
api_key = "hardcoded-secret-key"
```

## 📚 Code Review Guidelines

### Review Checklist

- [ ] **Code Quality**: Follows PEP 8 and project standards
- [ ] **Type Hints**: All functions have proper type hints
- [ ] **Documentation**: Functions and classes have docstrings
- [ ] **Tests**: New code has corresponding tests
- [ ] **Error Handling**: Proper exception handling
- [ ] **Security**: No hardcoded secrets or vulnerabilities
- [ ] **Performance**: No obvious performance issues
- [ ] **Logging**: Appropriate logging for debugging

### Review Process

1. **Create Pull Request**: Include description and tests
2. **Automated Checks**: Ensure CI/CD pipeline passes
3. **Code Review**: At least one approval required
4. **Merge**: Only after approval and all checks pass

## 🚨 Common Issues

### Import Errors

```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Install missing dependencies
pip install -r requirements-dev.txt
```

### Test Failures

```bash
# Run tests with verbose output
python -m pytest tests/ -v

# Run specific failing test
python -m pytest tests/test_signal_engine.py::TestSignalEngine::test_specific_function -v

# Debug test
python -m pytest tests/test_signal_engine.py -s --pdb
```

### Docker Build Issues

```bash
# Clean Docker cache
make docker-clean

# Rebuild without cache
docker build --no-cache -t petrosa/ta-bot:latest .

# Check Docker logs
docker logs <container-id>
```

## 📋 Development Checklist

- [ ] **Environment Setup**: Python 3.11+, dependencies installed
- [ ] **Code Quality**: Linting passes, code formatted
- [ ] **Tests**: All tests pass, coverage adequate
- [ ] **Documentation**: Code documented, README updated
- [ ] **Security**: No vulnerabilities, secrets properly handled
- [ ] **Performance**: No obvious performance issues
- [ ] **Integration**: Works with other components
- [ ] **Deployment**: Can be deployed successfully

## 🔗 Related Documentation

- **Testing Guide**: See [Testing Guide](./TESTING.md) for detailed testing
- **API Reference**: Check [API Reference](./API_REFERENCE.md) for API details
- **Configuration**: Review [Configuration](./CONFIGURATION.md) for settings
- **Deployment**: Read [Deployment Guide](./DEPLOYMENT.md) for production

---

**Next Steps**:
- Read [Testing Guide](./TESTING.md) for testing best practices
- Check [API Reference](./API_REFERENCE.md) for API development
- Review [Configuration](./CONFIGURATION.md) for environment setup
