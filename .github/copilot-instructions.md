# GitHub Copilot Instructions - TA Bot

## Service Context

**Purpose**: Technical analysis engine processing market data through 28+ strategies to generate trading signals.

**Deployment**: Kubernetes Deployment with MongoDB leader election for singleton operation

**Role in Ecosystem**: Consumes market data → Generates signals → Publishes to Trade Engine

---

## Architecture

**Data Flow**:
```
NATS (market data) → TA Bot → Strategy Execution → Signal Generation → NATS (signals) → Trade Engine
                       ↓
                   MongoDB (config, audit, state)
```

**Key Components**:
- `ta_bot/strategies/` - 28+ technical analysis strategies
- `ta_bot/services/app_config_manager.py` - MongoDB configuration
- `ta_bot/api/` - FastAPI configuration endpoints
- `ta_bot/middleware/rate_limiter.py` - Config change rate limiting

---

## Service-Specific Patterns

### Strategy Pattern

```python
# ✅ GOOD - Strategy base class
class StrategyBase:
    def analyze(self, df: pd.DataFrame) -> Signal:
        pass

# All strategies inherit and implement analyze()
class RSIStrategy(StrategyBase):
    def analyze(self, df: pd.DataFrame) -> Signal:
        # RSI calculation and signal generation
        pass
```

### Configuration Management

```python
# ✅ Runtime config in MongoDB
config_manager.update_config({
    "strategy_enabled": True,
    "rsi_period": 14,
    "signal_threshold": 70
})

# ✅ Rate limiting for config changes
@rate_limited(max_per_minute=10, max_per_hour=50)
async def update_config(...):
    pass
```

### Leader Election

```python
# ✅ GOOD - MongoDB leader election
if await leader_elector.is_leader():
    await process_batch()
else:
    logger.info("Not leader, skipping processing")

# Ensures only one pod processes at a time
```

---

## Testing Patterns

```python
# Mock NATS consumer
@pytest.fixture
def mock_nats():
    with patch('nats.connect') as mock:
        yield mock

# Test strategy logic
def test_rsi_strategy():
    df = create_sample_ohlcv_data()
    signal = RSIStrategy().analyze(df)
    assert signal.direction in ["BUY", "SELL", "HOLD"]
```

---

## Common Issues

**No Signal Generation**: Check strategy enabled in config
**High Latency**: Review DataFrame size and strategy complexity
**Leader Election Failures**: Check MongoDB connectivity

---

**Master Rules**: See `.cursorrules` in `petrosa_k8s` repo
**Service Rules**: `.cursorrules` in this repo
