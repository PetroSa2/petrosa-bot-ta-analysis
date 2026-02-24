# Signal Engine Documentation

Core analysis engine for the Petrosa TA Bot that coordinates all trading strategies and generates signals.

## 🏗️ Architecture Overview

The Signal Engine is the central component that:

1. **Receives candle data** from NATS messages
2. **Processes data** through multiple technical indicators
3. **Executes strategies** to analyze market conditions
4. **Generates signals** with confidence scores
5. **Publishes results** to external API endpoints

## 📊 Core Components

### Signal Engine (`ta_bot/core/signal_engine.py`)

```python
class SignalEngine:
    """Core signal generation engine."""

    def __init__(self):
        self.strategies = [
            MomentumPulseStrategy(),
            BandFadeReversalStrategy(),
            GoldenTrendSyncStrategy(),
            RangeBreakPopStrategy(),
            DivergenceTrapStrategy()
        ]
        self.indicators = TechnicalIndicators()
        self.confidence = ConfidenceCalculator()
```

### Technical Indicators (`ta_bot/core/indicators.py`)

```python
class TechnicalIndicators:
    """Technical analysis indicators calculator."""

    def calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> float
    def calculate_macd(self, data: pd.DataFrame) -> Dict[str, float]
    def calculate_bollinger_bands(self, data: pd.DataFrame) -> Dict[str, float]
    def calculate_adx(self, data: pd.DataFrame, period: int = 14) -> float
    def calculate_atr(self, data: pd.DataFrame, period: int = 14) -> float
```

### Confidence Calculator (`ta_bot/core/confidence.py`)

```python
class ConfidenceCalculator:
    """Calculate signal confidence based on multiple factors."""

    def calculate_confidence(self, signal: Signal, indicators: Dict) -> float
    def validate_signal_strength(self, signal: Signal) -> bool
    def adjust_for_market_conditions(self, confidence: float, market_data: Dict) -> float
```

## 🔄 Signal Processing Flow

### 1. Data Reception

```python
# NATS message format
{
    "symbol": "BTCUSDT",
    "period": "15m",
    "timestamp": 1640995200000,
    "open": 50000.0,
    "high": 50100.0,
    "low": 49900.0,
    "close": 50050.0,
    "volume": 1000.0
}
```

### 2. Indicator Calculation

```python
# Calculate all technical indicators
indicators = {
    "rsi": 58.3,
    "macd": {
        "macd": 0.0012,
        "signal": 0.0008,
        "histogram": 0.0004
    },
    "bollinger_bands": {
        "upper": 51000.0,
        "middle": 50000.0,
        "lower": 49000.0
    },
    "adx": 27.5,
    "atr": 150.0
}
```

### 3. Strategy Execution

```python
# Execute each strategy
for strategy in self.strategies:
    signal = strategy.analyze(candle_data, indicators)
    if signal:
        signals.append(signal)
```

### 4. Signal Generation

```python
# Generate final signal with confidence
final_signal = Signal(
    symbol="BTCUSDT",
    period="15m",
    signal="BUY",
    confidence=0.74,
    strategy="momentum_pulse",
    metadata=indicators
)
```

## 📈 Technical Indicators

### RSI (Relative Strength Index)

```python
def calculate_rsi(data: pd.DataFrame, period: int = 14) -> float:
    """Calculate RSI indicator."""
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]
```

**Usage**: Overbought/oversold conditions, divergence detection

### MACD (Moving Average Convergence Divergence)

```python
def calculate_macd(data: pd.DataFrame) -> Dict[str, float]:
    """Calculate MACD indicator."""
    exp1 = data['close'].ewm(span=12).mean()
    exp2 = data['close'].ewm(span=26).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9).mean()
    histogram = macd - signal

    return {
        "macd": macd.iloc[-1],
        "signal": signal.iloc[-1],
        "histogram": histogram.iloc[-1]
    }
```

**Usage**: Trend direction, momentum confirmation

### Bollinger Bands

```python
def calculate_bollinger_bands(data: pd.DataFrame, period: int = 20, std: float = 2.0) -> Dict[str, float]:
    """Calculate Bollinger Bands."""
    sma = data['close'].rolling(window=period).mean()
    std_dev = data['close'].rolling(window=period).std()

    return {
        "upper": sma + (std_dev * std),
        "middle": sma,
        "lower": sma - (std_dev * std)
    }
```

**Usage**: Volatility measurement, support/resistance levels

### ADX (Average Directional Index)

```python
def calculate_adx(data: pd.DataFrame, period: int = 14) -> float:
    """Calculate ADX indicator."""
    # Implementation details for ADX calculation
    # Returns trend strength (0-100)
    return adx_value
```

**Usage**: Trend strength measurement

### ATR (Average True Range)

```python
def calculate_atr(data: pd.DataFrame, period: int = 14) -> float:
    """Calculate ATR indicator."""
    high_low = data['high'] - data['low']
    high_close = np.abs(data['high'] - data['close'].shift())
    low_close = np.abs(data['low'] - data['close'].shift())

    true_range = np.maximum(high_low, np.maximum(high_close, low_close))
    atr = true_range.rolling(window=period).mean()
    return atr.iloc[-1]
```

**Usage**: Volatility measurement, stop-loss calculation

## 🎯 Strategy Integration

### Strategy Interface

```python
class BaseStrategy(ABC):
    """Base class for all trading strategies."""

    @abstractmethod
    def analyze(self, candle_data: pd.DataFrame, indicators: Dict) -> Optional[Signal]:
        """Analyze market data and return signal if conditions are met."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return strategy name."""
        pass
```

### Strategy Execution

```python
def process_candle(self, candle_data: pd.DataFrame) -> List[Signal]:
    """Process candle data through all strategies."""
    signals = []

    # Calculate indicators
    indicators = self.indicators.calculate_all(candle_data)

    # Execute strategies
    for strategy in self.strategies:
        signal = strategy.analyze(candle_data, indicators)
        if signal:
            # Calculate confidence
            signal.confidence = self.confidence.calculate_confidence(signal, indicators)
            signals.append(signal)

    return signals
```

## 📊 Signal Format

### Signal Model

```python
@dataclass
class Signal:
    symbol: str
    period: str
    signal: str  # "BUY" or "SELL"
    confidence: float  # 0.0 to 1.0
    strategy: str
    metadata: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
```

### Signal Output

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
    "adx": 27,
    "bollinger_position": 0.6,
    "atr": 150.0
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 🔧 Configuration

### Environment Variables

```bash
# Technical Analysis Settings
TA_BOT_RSI_PERIOD=14
TA_BOT_MACD_FAST=12
TA_BOT_MACD_SLOW=26
TA_BOT_MACD_SIGNAL=9
TA_BOT_ADX_PERIOD=14
TA_BOT_BB_PERIOD=20
TA_BOT_BB_STD=2.0
TA_BOT_ATR_PERIOD=14

# Confidence Settings
TA_BOT_MIN_CONFIDENCE=0.6
TA_BOT_CONFIDENCE_WEIGHTS={"rsi": 0.2, "macd": 0.3, "adx": 0.2, "bb": 0.2, "atr": 0.1}
```

### Kubernetes ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ta-bot-config
  namespace: petrosa-apps
data:
  rsi_period: "14"
  macd_fast: "12"
  macd_slow: "26"
  macd_signal: "9"
  adx_period: "14"
  bb_period: "20"
  bb_std: "2.0"
  atr_period: "14"
  min_confidence: "0.6"
```

## 🚀 Performance Optimization

### Caching

```python
class IndicatorCache:
    """Cache calculated indicators for performance."""

    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.max_size = max_size

    def get(self, key: str) -> Optional[Dict]:
        """Get cached indicators."""
        return self.cache.get(key)

    def set(self, key: str, indicators: Dict):
        """Cache indicators."""
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        self.cache[key] = indicators
```

### Parallel Processing

```python
async def process_strategies_parallel(self, candle_data: pd.DataFrame, indicators: Dict) -> List[Signal]:
    """Process strategies in parallel for better performance."""
    tasks = []
    for strategy in self.strategies:
        task = asyncio.create_task(strategy.analyze_async(candle_data, indicators))
        tasks.append(task)

    results = await asyncio.gather(*tasks, return_exceptions=True)
    signals = [result for result in results if result is not None]
    return signals
```

## 📈 Monitoring & Metrics

### Key Metrics

```python
class SignalEngineMetrics:
    """Metrics for signal engine performance."""

    def __init__(self):
        self.signals_generated = 0
        self.processing_time = 0.0
        self.strategy_performance = {}

    def record_signal(self, strategy: str, confidence: float):
        """Record signal generation."""
        self.signals_generated += 1
        if strategy not in self.strategy_performance:
            self.strategy_performance[strategy] = []
        self.strategy_performance[strategy].append(confidence)

    def get_metrics(self) -> Dict:
        """Get current metrics."""
        return {
            "total_signals": self.signals_generated,
            "avg_processing_time": self.processing_time,
            "strategy_performance": {
                strategy: {
                    "count": len(confidences),
                    "avg_confidence": sum(confidences) / len(confidences)
                }
                for strategy, confidences in self.strategy_performance.items()
            }
        }
```

### Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Metrics
SIGNALS_GENERATED = Counter('ta_bot_signals_generated_total', 'Total signals generated', ['strategy'])
SIGNAL_CONFIDENCE = Histogram('ta_bot_signal_confidence', 'Signal confidence distribution', ['strategy'])
PROCESSING_TIME = Histogram('ta_bot_processing_time_seconds', 'Signal processing time')
ACTIVE_STRATEGIES = Gauge('ta_bot_active_strategies', 'Number of active strategies')
```

## 🔍 Testing

### Unit Tests

```python
def test_signal_engine_initialization():
    """Test signal engine initialization."""
    engine = SignalEngine()
    assert len(engine.strategies) == 5
    assert engine.indicators is not None
    assert engine.confidence is not None

def test_indicator_calculation():
    """Test technical indicator calculations."""
    indicators = TechnicalIndicators()
    data = create_test_candle_data()

    rsi = indicators.calculate_rsi(data)
    assert 0 <= rsi <= 100

    macd = indicators.calculate_macd(data)
    assert "macd" in macd
    assert "signal" in macd
    assert "histogram" in macd

def test_confidence_calculation():
    """Test confidence calculation."""
    calculator = ConfidenceCalculator()
    signal = Signal(symbol="BTCUSDT", signal="BUY", confidence=0.0)
    indicators = {"rsi": 70, "macd_hist": 0.001}

    confidence = calculator.calculate_confidence(signal, indicators)
    assert 0.0 <= confidence <= 1.0
```

### Integration Tests

```python
async def test_signal_engine_integration():
    """Test complete signal engine integration."""
    engine = SignalEngine()
    candle_data = create_test_candle_data()

    signals = await engine.process_candle(candle_data)
    assert isinstance(signals, list)

    for signal in signals:
        assert signal.symbol == "BTCUSDT"
        assert signal.confidence > 0.0
        assert signal.confidence <= 1.0
```

## 🚨 Error Handling

### Exception Handling

```python
class SignalEngineError(Exception):
    """Base exception for signal engine errors."""
    pass

class IndicatorCalculationError(SignalEngineError):
    """Error during indicator calculation."""
    pass

class StrategyExecutionError(SignalEngineError):
    """Error during strategy execution."""
    pass

def safe_calculate_indicators(self, data: pd.DataFrame) -> Dict:
    """Safely calculate indicators with error handling."""
    try:
        return self.indicators.calculate_all(data)
    except Exception as e:
        logger.error(f"Indicator calculation failed: {e}")
        raise IndicatorCalculationError(f"Failed to calculate indicators: {e}")
```

### Recovery Mechanisms

```python
def process_with_recovery(self, candle_data: pd.DataFrame) -> List[Signal]:
    """Process candle data with recovery mechanisms."""
    try:
        return self.process_candle(candle_data)
    except IndicatorCalculationError:
        logger.warning("Indicator calculation failed, using cached data")
        return self.process_with_cached_indicators(candle_data)
    except StrategyExecutionError:
        logger.warning("Strategy execution failed, skipping problematic strategies")
        return self.process_with_fallback_strategies(candle_data)
    except Exception as e:
        logger.error(f"Unexpected error in signal engine: {e}")
        return []
```

## 📚 Related Documentation

- **Trading Strategies**: See [Strategies](./STRATEGIES.md) for individual strategy details
- **API Reference**: Check [API Reference](./API_REFERENCE.md) for signal output format
- **Configuration**: Review [Configuration](./CONFIGURATION.md) for environment setup
- **Architecture**: Read [Architecture Overview](./ARCHITECTURE.md) for system design

---

**Next Steps**:
- Review [Trading Strategies](./STRATEGIES.md) for strategy-specific details
- Check [Configuration](./CONFIGURATION.md) for environment setup
- See [API Reference](./API_REFERENCE.md) for signal output format
