# Architecture Overview

The Petrosa TA Bot is designed as a microservice-based technical analysis system for cryptocurrency trading.

## 🏗️ System Architecture

### High-Level Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   NATS Server   │    │   TA Bot        │    │   REST API      │
│                 │    │                 │    │                 │
│ • Candle Data   │───▶│ • Signal Engine │───▶│ • Signal Output │
│ • Market Events │    │ • Strategies    │    │ • Position Mgmt │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Core Components

#### 1. **NATS Listener Service**
- **Purpose**: Subscribes to real-time candle updates
- **Input**: NATS messages with OHLCV data
- **Output**: Structured candle data for analysis

#### 2. **Signal Engine**
- **Purpose**: Coordinates all trading strategies
- **Input**: Candle data and indicators
- **Output**: Trading signals with confidence scores

#### 3. **Strategy Modules**
- **Purpose**: Individual technical analysis strategies
- **Input**: Candle data and calculated indicators
- **Output**: Buy/Sell signals with metadata

#### 4. **REST Publisher**
- **Purpose**: Sends signals to external trading systems
- **Input**: Generated trading signals
- **Output**: HTTP POST requests to API endpoints

## 🔧 Component Details

### NATS Listener Service

```python
class NATSListener:
    def __init__(self, nats_url: str):
        self.nats_url = nats_url
        self.signal_engine = SignalEngine()
        self.publisher = RESTPublisher()
    
    async def handle_candle_update(self, message):
        # Parse candle data
        # Run signal analysis
        # Publish signals
```

**Message Format**:
```json
{
  "symbol": "BTCUSDT",
  "period": "15m",
  "candles": [
    {
      "timestamp": "2024-01-01T00:00:00Z",
      "open": 50000.0,
      "high": 50100.0,
      "low": 49900.0,
      "close": 50050.0,
      "volume": 1000.0
    }
  ]
}
```

### Signal Engine

```python
class SignalEngine:
    def __init__(self):
        self.strategies = {
            'momentum_pulse': MomentumPulseStrategy(),
            'band_fade_reversal': BandFadeReversalStrategy(),
            'golden_trend_sync': GoldenTrendSyncStrategy(),
            'range_break_pop': RangeBreakPopStrategy(),
            'divergence_trap': DivergenceTrapStrategy()
        }
    
    def analyze_candles(self, candles, symbol, period):
        # Calculate indicators
        # Run all strategies
        # Return signals
```

**Process Flow**:
1. **Indicator Calculation**: RSI, MACD, ADX, EMAs, Bollinger Bands
2. **Strategy Execution**: Run each strategy independently
3. **Signal Aggregation**: Collect and validate signals
4. **Confidence Scoring**: Calculate confidence for each signal

### Strategy Modules

Each strategy follows a common interface:

```python
class BaseStrategy:
    def analyze(self, df: pd.DataFrame, indicators: dict) -> Optional[Signal]:
        # Strategy-specific logic
        # Return Signal object or None
```

**Strategy Types**:
- **Trend Following**: Momentum Pulse, Golden Trend Sync
- **Mean Reversion**: Band Fade Reversal
- **Breakout**: Range Break Pop
- **Divergence**: Divergence Trap

### REST Publisher

```python
class RESTPublisher:
    def __init__(self, api_endpoint: str):
        self.api_endpoint = api_endpoint
    
    async def publish_signal(self, signal: Signal):
        # Send HTTP POST request
        # Handle response and errors
```

## 📊 Data Flow

### 1. Data Ingestion
```
NATS Message → NATS Listener → Candle DataFrame
```

### 2. Analysis Pipeline
```
Candle DataFrame → Indicator Calculation → Strategy Analysis → Signal Generation
```

### 3. Signal Output
```
Signal Object → REST Publisher → External API
```

## 🎯 Trading Strategies

### Strategy 1: Momentum Pulse
- **Type**: Trend Following
- **Trigger**: MACD histogram crossover
- **Confidence**: Base 0.6 + RSI/EMA modifiers

### Strategy 2: Band Fade Reversal
- **Type**: Mean Reversion
- **Trigger**: Bollinger Band breakout reversal
- **Confidence**: Base 0.55 + volatility modifiers

### Strategy 3: Golden Trend Sync
- **Type**: Trend Following
- **Trigger**: EMA pullback entry
- **Confidence**: Base 0.65 + trend strength modifiers

### Strategy 4: Range Break Pop
- **Type**: Breakout
- **Trigger**: Volatility breakout
- **Confidence**: Base 0.6 + volume/ATR modifiers

### Strategy 5: Divergence Trap
- **Type**: Divergence
- **Trigger**: Hidden bullish divergence
- **Confidence**: Base 0.6 + divergence strength modifiers

## 🔄 Signal Lifecycle

### 1. **Signal Generation**
```python
signal = Signal(
    symbol="BTCUSDT",
    period="15m",
    signal=SignalType.BUY,
    confidence=0.74,
    strategy="momentum_pulse",
    metadata={"rsi": 58.3, "macd_hist": 0.0012}
)
```

### 2. **Signal Validation**
- Check confidence thresholds
- Validate metadata
- Ensure proper formatting

### 3. **Signal Publishing**
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
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## 🏥 Health Monitoring

### Health Endpoints
- `/health` - Detailed system health
- `/ready` - Readiness probe
- `/live` - Liveness probe

### Metrics
- Signal generation rate
- Strategy performance
- Error rates
- Response times

## 🔒 Security Architecture

### Network Security
- **NATS**: TLS encryption for message transport
- **REST API**: HTTPS with authentication
- **Kubernetes**: Network policies and RBAC

### Data Security
- **No sensitive data logging**
- **Environment variable configuration**
- **Secret management via Kubernetes**

## 📈 Scalability

### Horizontal Scaling
- **Kubernetes HPA**: Auto-scaling based on CPU/memory
- **Multiple replicas**: 3+ instances for high availability
- **Load balancing**: Service mesh for traffic distribution

### Performance Optimization
- **Async processing**: Non-blocking I/O operations
- **Memory management**: Efficient pandas operations
- **Caching**: Indicator calculation caching

## 🐳 Container Architecture

### Docker Image
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY ta_bot/ .
CMD ["python", "-m", "ta_bot.main"]
```

### Kubernetes Deployment
- **Namespace**: `petrosa-apps`
- **Replicas**: 3 (configurable)
- **Resources**: CPU/memory limits
- **Health checks**: Liveness/readiness probes

## 🔧 Configuration Management

### Environment Variables
```bash
# Required
NATS_URL=nats://nats-server:4222
API_ENDPOINT=http://api-server:8080/signals

# Optional
LOG_LEVEL=INFO
ENVIRONMENT=production
SUPPORTED_SYMBOLS=BTCUSDT,ETHUSDT
SUPPORTED_TIMEFRAMES=15m,1h
```

### Kubernetes ConfigMaps
- **Configuration**: Non-sensitive settings
- **Secrets**: Sensitive data (API keys, tokens)

## 🚀 Deployment Architecture

### Remote MicroK8s Cluster
- **Server**: `https://192.168.194.253:16443`
- **Namespace**: `petrosa-apps`
- **Ingress**: SSL-enabled with Let's Encrypt

### CI/CD Pipeline
1. **Lint**: Code quality checks
2. **Test**: Unit tests with coverage
3. **Security**: Vulnerability scanning
4. **Build**: Docker image creation
5. **Deploy**: Kubernetes deployment

---

**Next Steps**:
- Read [Trading Strategies](./STRATEGIES.md) for detailed strategy documentation
- Check [Signal Engine](./SIGNAL_ENGINE.md) for core analysis engine details
- Review [API Reference](./API_REFERENCE.md) for REST API documentation 