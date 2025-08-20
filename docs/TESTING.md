# Testing Guide

Comprehensive testing guide for the Petrosa TA Bot.

## 🧪 Testing Overview

### Testing Philosophy

- **Test-Driven Development**: Write tests before implementation
- **Comprehensive Coverage**: Aim for >90% code coverage
- **Fast Execution**: Tests should run quickly (<30 seconds)
- **Isolated Tests**: Each test should be independent
- **Realistic Data**: Use realistic market data for testing

### Testing Pyramid

```
    /\
   /  \     E2E Tests (Few)
  /____\
 /      \   Integration Tests (Some)
/________\  Unit Tests (Many)
```

## 📋 Test Structure

### Directory Organization

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests
│   ├── test_signal_engine.py
│   ├── test_indicators.py
│   ├── test_confidence.py
│   └── test_strategies/
│       ├── test_momentum_pulse.py
│       ├── test_band_fade_reversal.py
│       └── ...
├── integration/             # Integration tests
│   ├── test_nats_integration.py
│   ├── test_api_integration.py
│   └── test_signal_pipeline.py
└── e2e/                    # End-to-end tests
    ├── test_complete_workflow.py
    └── test_deployment.py
```

### Test File Naming

- **Unit tests**: `test_<module_name>.py`
- **Integration tests**: `test_<component>_integration.py`
- **E2E tests**: `test_<workflow>_e2e.py`

## 🚀 Running Tests

### Basic Commands

```bash
# Run all tests
make test

# Run with coverage
python -m pytest tests/ --cov=ta_bot --cov-report=html

# Run specific test file
python -m pytest tests/test_signal_engine.py -v

# Run specific test function
python -m pytest tests/test_signal_engine.py::TestSignalEngine::test_initialization -v

# Run tests with markers
python -m pytest tests/ -m "unit"
python -m pytest tests/ -m "integration"
python -m pytest tests/ -m "e2e"
```

### Test Categories

```bash
# Unit tests only
python -m pytest tests/unit/ -v

# Integration tests only
python -m pytest tests/integration/ -v

# E2E tests only
python -m pytest tests/e2e/ -v
```

### Coverage Reports

```bash
# Generate HTML coverage report
python -m pytest tests/ --cov=ta_bot --cov-report=html

# Generate XML coverage report (for CI)
python -m pytest tests/ --cov=ta_bot --cov-report=xml

# Generate terminal coverage report
python -m pytest tests/ --cov=ta_bot --cov-report=term
```

## 📊 Test Fixtures

### Common Fixtures (`tests/conftest.py`)

```python
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

@pytest.fixture
def sample_candle_data():
    """Create sample OHLCV data for testing."""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    return pd.DataFrame({
        'timestamp': dates,
        'open': np.random.uniform(50000, 51000, 100),
        'high': np.random.uniform(50100, 51100, 100),
        'low': np.random.uniform(49900, 50900, 100),
        'close': np.random.uniform(50000, 51000, 100),
        'volume': np.random.uniform(1000, 2000, 100)
    })

@pytest.fixture
def sample_indicators():
    """Create sample technical indicators for testing."""
    return {
        'rsi': 58.3,
        'macd': {
            'macd': 0.0012,
            'signal': 0.0008,
            'histogram': 0.0004
        },
        'bollinger_bands': {
            'upper': 51000.0,
            'middle': 50000.0,
            'lower': 49000.0
        },
        'adx': 27.5,
        'atr': 150.0
    }

@pytest.fixture
def mock_nats_connection():
    """Mock NATS connection for testing."""
    class MockNATSConnection:
        def subscribe(self, subject, callback):
            return "subscription_id"

        def publish(self, subject, payload):
            return True

        def close(self):
            return True

    return MockNATSConnection()

@pytest.fixture
def mock_api_client():
    """Mock API client for testing."""
    class MockAPIClient:
        def post(self, url, json=None):
            return MockResponse(200, {"status": "success"})

    return MockAPIClient()

class MockResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json = json_data

    def json(self):
        return self._json
```

## 🧪 Unit Tests

### Signal Engine Tests

```python
# tests/unit/test_signal_engine.py
import pytest
import pandas as pd
from ta_bot.core.signal_engine import SignalEngine
from ta_bot.models.signal import Signal

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
        assert signal_engine.confidence is not None

    def test_process_candle(self, signal_engine, sample_candle_data):
        """Test candle processing."""
        signals = signal_engine.process_candle(sample_candle_data)
        assert isinstance(signals, list)

        for signal in signals:
            assert isinstance(signal, Signal)
            assert signal.symbol in ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
            assert signal.confidence >= 0.0
            assert signal.confidence <= 1.0

    def test_empty_data_handling(self, signal_engine):
        """Test handling of empty data."""
        empty_data = pd.DataFrame()
        signals = signal_engine.process_candle(empty_data)
        assert signals == []

    def test_invalid_data_handling(self, signal_engine):
        """Test handling of invalid data."""
        invalid_data = pd.DataFrame({'invalid': [1, 2, 3]})
        with pytest.raises(ValueError):
            signal_engine.process_candle(invalid_data)
```

### Indicator Tests

```python
# tests/unit/test_indicators.py
import pytest
import pandas as pd
import numpy as np
from ta_bot.core.indicators import TechnicalIndicators

class TestTechnicalIndicators:
    """Test cases for TechnicalIndicators."""

    @pytest.fixture
    def indicators(self):
        """Create TechnicalIndicators instance."""
        return TechnicalIndicators()

    @pytest.fixture
    def sample_data(self):
        """Create sample data for indicator testing."""
        return pd.DataFrame({
            'close': [100, 101, 102, 101, 100, 99, 98, 97, 96, 95],
            'high': [102, 103, 104, 103, 102, 101, 100, 99, 98, 97],
            'low': [98, 99, 100, 99, 98, 97, 96, 95, 94, 93]
        })

    def test_rsi_calculation(self, indicators, sample_data):
        """Test RSI calculation."""
        rsi = indicators.calculate_rsi(sample_data, period=14)
        assert 0 <= rsi <= 100
        assert isinstance(rsi, float)

    def test_macd_calculation(self, indicators, sample_data):
        """Test MACD calculation."""
        macd = indicators.calculate_macd(sample_data)
        assert 'macd' in macd
        assert 'signal' in macd
        assert 'histogram' in macd
        assert all(isinstance(v, float) for v in macd.values())

    def test_bollinger_bands_calculation(self, indicators, sample_data):
        """Test Bollinger Bands calculation."""
        bb = indicators.calculate_bollinger_bands(sample_data)
        assert 'upper' in bb
        assert 'middle' in bb
        assert 'lower' in bb
        assert bb['upper'] > bb['middle'] > bb['lower']

    def test_adx_calculation(self, indicators, sample_data):
        """Test ADX calculation."""
        adx = indicators.calculate_adx(sample_data)
        assert 0 <= adx <= 100
        assert isinstance(adx, float)

    def test_atr_calculation(self, indicators, sample_data):
        """Test ATR calculation."""
        atr = indicators.calculate_atr(sample_data)
        assert atr > 0
        assert isinstance(atr, float)
```

### Strategy Tests

```python
# tests/unit/test_strategies/test_momentum_pulse.py
import pytest
import pandas as pd
from ta_bot.strategies.momentum_pulse import MomentumPulseStrategy
from ta_bot.models.signal import Signal

class TestMomentumPulseStrategy:
    """Test cases for MomentumPulseStrategy."""

    @pytest.fixture
    def strategy(self):
        """Create strategy instance."""
        return MomentumPulseStrategy()

    @pytest.fixture
    def bullish_data(self):
        """Create bullish market data."""
        return pd.DataFrame({
            'close': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
            'high': [102, 103, 104, 105, 106, 107, 108, 109, 110, 111],
            'low': [98, 99, 100, 101, 102, 103, 104, 105, 106, 107]
        })

    @pytest.fixture
    def bearish_data(self):
        """Create bearish market data."""
        return pd.DataFrame({
            'close': [109, 108, 107, 106, 105, 104, 103, 102, 101, 100],
            'high': [111, 110, 109, 108, 107, 106, 105, 104, 103, 102],
            'low': [107, 106, 105, 104, 103, 102, 101, 100, 99, 98]
        })

    def test_strategy_name(self, strategy):
        """Test strategy name."""
        assert strategy.get_name() == "momentum_pulse"

    def test_bullish_signal(self, strategy, bullish_data, sample_indicators):
        """Test bullish signal generation."""
        signal = strategy.analyze(bullish_data, sample_indicators)
        if signal:
            assert signal.signal == "BUY"
            assert signal.confidence > 0.5

    def test_bearish_signal(self, strategy, bearish_data, sample_indicators):
        """Test bearish signal generation."""
        signal = strategy.analyze(bearish_data, sample_indicators)
        if signal:
            assert signal.signal == "SELL"
            assert signal.confidence > 0.5

    def test_no_signal_conditions(self, strategy, sample_candle_data, sample_indicators):
        """Test conditions where no signal is generated."""
        signal = strategy.analyze(sample_candle_data, sample_indicators)
        # May or may not generate signal depending on conditions
        if signal:
            assert signal.confidence > 0.0
```

## 🔗 Integration Tests

### NATS Integration Tests

```python
# tests/integration/test_nats_integration.py
import pytest
import asyncio
from unittest.mock import Mock, patch
from ta_bot.services.nats_listener import NATSListener

class TestNATSIntegration:
    """Test NATS integration."""

    @pytest.fixture
    def nats_listener(self):
        """Create NATS listener for testing."""
        signal_engine = Mock()
        publisher = Mock()
        return NATSListener(
            nats_url="nats://localhost:4222",
            signal_engine=signal_engine,
            publisher=publisher
        )

    @pytest.mark.asyncio
    async def test_connection_establishment(self, nats_listener):
        """Test NATS connection establishment."""
        with patch('nats.aio.connect') as mock_connect:
            mock_connect.return_value = Mock()
            await nats_listener.start()
            mock_connect.assert_called_once_with("nats://localhost:4222")

    @pytest.mark.asyncio
    async def test_message_processing(self, nats_listener):
        """Test message processing."""
        test_message = {
            "symbol": "BTCUSDT",
            "period": "15m",
            "timestamp": 1640995200000,
            "open": 50000.0,
            "high": 50100.0,
            "low": 49900.0,
            "close": 50050.0,
            "volume": 1000.0
        }

        # Mock the callback
        callback_called = False
        def mock_callback(msg):
            nonlocal callback_called
            callback_called = True
            assert msg.data == test_message

        nats_listener._process_message = mock_callback
        await nats_listener._handle_message(test_message)
        assert callback_called
```

### API Integration Tests

```python
# tests/integration/test_api_integration.py
import pytest
import requests
from unittest.mock import Mock, patch
from ta_bot.services.publisher import SignalPublisher

class TestAPIIntegration:
    """Test API integration."""

    @pytest.fixture
    def publisher(self):
        """Create signal publisher for testing."""
        return SignalPublisher("http://localhost:8080/signals")

    def test_signal_publishing(self, publisher):
        """Test signal publishing to API."""
        test_signal = {
            "symbol": "BTCUSDT",
            "period": "15m",
            "signal": "BUY",
            "confidence": 0.74,
            "strategy": "momentum_pulse",
            "metadata": {"rsi": 58.3}
        }

        with patch('requests.post') as mock_post:
            mock_post.return_value = Mock(status_code=200)
            result = publisher.publish_signal(test_signal)
            assert result is True
            mock_post.assert_called_once()

    def test_api_error_handling(self, publisher):
        """Test API error handling."""
        test_signal = {"symbol": "BTCUSDT", "signal": "BUY"}

        with patch('requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError()
            result = publisher.publish_signal(test_signal)
            assert result is False
```

## 🌐 End-to-End Tests

### Complete Workflow Tests

```python
# tests/e2e/test_complete_workflow.py
import pytest
import asyncio
from unittest.mock import Mock, patch
from ta_bot.main import main

class TestCompleteWorkflow:
    """Test complete application workflow."""

    @pytest.mark.asyncio
    async def test_complete_signal_generation(self):
        """Test complete signal generation workflow."""
        # Mock external dependencies
        with patch('ta_bot.services.nats_listener.NATSListener') as mock_nats, \
             patch('ta_bot.services.publisher.SignalPublisher') as mock_publisher:

            # Setup mocks
            mock_nats_instance = Mock()
            mock_nats.return_value = mock_nats_instance

            mock_publisher_instance = Mock()
            mock_publisher.return_value = mock_publisher_instance

            # Run main function
            try:
                await main()
            except KeyboardInterrupt:
                # Expected when running in test mode
                pass

            # Verify components were initialized
            mock_nats.assert_called_once()
            mock_publisher.assert_called_once()

    @pytest.mark.asyncio
    async def test_signal_pipeline(self):
        """Test complete signal pipeline."""
        from ta_bot.core.signal_engine import SignalEngine
        from ta_bot.services.nats_listener import NATSListener
        from ta_bot.services.publisher import SignalPublisher

        # Create components
        signal_engine = SignalEngine()
        publisher = SignalPublisher("http://localhost:8080/signals")
        nats_listener = NATSListener(
            nats_url="nats://localhost:4222",
            signal_engine=signal_engine,
            publisher=publisher
        )

        # Test data flow
        test_candle = {
            "symbol": "BTCUSDT",
            "period": "15m",
            "timestamp": 1640995200000,
            "open": 50000.0,
            "high": 50100.0,
            "low": 49900.0,
            "close": 50050.0,
            "volume": 1000.0
        }

        # Process candle through pipeline
        signals = signal_engine.process_candle(test_candle)
        assert isinstance(signals, list)

        # Verify signal structure
        for signal in signals:
            assert hasattr(signal, 'symbol')
            assert hasattr(signal, 'signal')
            assert hasattr(signal, 'confidence')
```

## 📊 Performance Tests

### Load Testing

```python
# tests/performance/test_load.py
import pytest
import time
import asyncio
from ta_bot.core.signal_engine import SignalEngine

class TestPerformance:
    """Performance tests."""

    @pytest.fixture
    def signal_engine(self):
        """Create signal engine for performance testing."""
        return SignalEngine()

    def test_signal_generation_performance(self, signal_engine, sample_candle_data):
        """Test signal generation performance."""
        start_time = time.time()

        # Process multiple candles
        for _ in range(100):
            signals = signal_engine.process_candle(sample_candle_data)

        end_time = time.time()
        processing_time = end_time - start_time

        # Should process 100 candles in under 1 second
        assert processing_time < 1.0
        print(f"Processed 100 candles in {processing_time:.3f} seconds")

    def test_memory_usage(self, signal_engine, sample_candle_data):
        """Test memory usage during processing."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Process many candles
        for _ in range(1000):
            signals = signal_engine.process_candle(sample_candle_data)

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (< 100MB)
        assert memory_increase < 100 * 1024 * 1024
        print(f"Memory increase: {memory_increase / 1024 / 1024:.2f} MB")
```

## 🔍 Test Utilities

### Test Data Generators

```python
# tests/utils/test_data.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_candle_data(
    symbol: str = "BTCUSDT",
    periods: int = 100,
    start_price: float = 50000.0,
    volatility: float = 0.02
) -> pd.DataFrame:
    """Generate realistic candle data for testing."""
    dates = pd.date_range(
        start=datetime.now() - timedelta(days=periods),
        periods=periods,
        freq='15min'
    )

    # Generate price series with random walk
    price_changes = np.random.normal(0, volatility, periods)
    prices = [start_price]

    for change in price_changes[1:]:
        new_price = prices[-1] * (1 + change)
        prices.append(new_price)

    # Generate OHLCV data
    data = []
    for i, (date, close) in enumerate(zip(dates, prices)):
        high = close * (1 + abs(np.random.normal(0, 0.005)))
        low = close * (1 - abs(np.random.normal(0, 0.005)))
        open_price = prices[i-1] if i > 0 else close
        volume = np.random.uniform(1000, 2000)

        data.append({
            'timestamp': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })

    return pd.DataFrame(data)

def generate_signals(count: int = 10) -> list:
    """Generate sample signals for testing."""
    signals = []
    strategies = ["momentum_pulse", "band_fade_reversal", "golden_trend_sync"]

    for i in range(count):
        signal = {
            "symbol": "BTCUSDT",
            "period": "15m",
            "signal": "BUY" if i % 2 == 0 else "SELL",
            "confidence": np.random.uniform(0.6, 0.9),
            "strategy": strategies[i % len(strategies)],
            "metadata": {
                "rsi": np.random.uniform(30, 70),
                "macd_hist": np.random.uniform(-0.001, 0.001),
                "adx": np.random.uniform(20, 40)
            },
            "timestamp": datetime.now().isoformat()
        }
        signals.append(signal)

    return signals
```

## 🚨 Test Configuration

### pytest.ini

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --strict-markers
    --disable-warnings
    --cov=ta_bot
    --cov-report=term-missing
    --cov-report=html
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow running tests
    performance: Performance tests
```

### Coverage Configuration

```ini
[coverage:run]
source = ta_bot
omit =
    */tests/*
    */__pycache__/*
    */migrations/*

[coverage:report]
exclude_lines =
    pragma: no cover
    def __repr__
    if self.debug:
    if settings.DEBUG
    raise AssertionError
    raise NotImplementedError
    if 0:
    if __name__ == .__main__.:
    class .*\bProtocol\):
    @(abc\.)?abstractmethod
```

## 📋 Testing Checklist

### Before Running Tests

- [ ] **Environment**: Python 3.11+ installed
- [ ] **Dependencies**: All test dependencies installed
- [ ] **Configuration**: Test environment variables set
- [ ] **Database**: Test database ready (if applicable)
- [ ] **Services**: Mock services configured

### Test Quality

- [ ] **Coverage**: >90% code coverage achieved
- [ ] **Speed**: All tests complete in <30 seconds
- [ ] **Isolation**: Tests don't interfere with each other
- [ ] **Realistic**: Tests use realistic data
- [ ] **Maintainable**: Tests are easy to understand and modify

### Test Categories

- [ ] **Unit Tests**: All functions and classes tested
- [ ] **Integration Tests**: Component interactions tested
- [ ] **E2E Tests**: Complete workflows tested
- [ ] **Performance Tests**: Performance benchmarks included
- [ ] **Security Tests**: Security vulnerabilities tested

## 🔗 Related Documentation

- **Development Guide**: See [Development Guide](./DEVELOPMENT.md) for development workflow
- **API Reference**: Check [API Reference](./API_REFERENCE.md) for API testing
- **Configuration**: Review [Configuration](./CONFIGURATION.md) for test configuration
- **Deployment**: Read [Deployment Guide](./DEPLOYMENT.md) for deployment testing

---

**Next Steps**:
- Read [Development Guide](./DEVELOPMENT.md) for development workflow
- Check [API Reference](./API_REFERENCE.md) for API testing
- Review [Configuration](./CONFIGURATION.md) for test setup
