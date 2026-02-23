# OpenTelemetry Tracing - Span Attribute Naming Convention

This document describes the standardized naming convention for OpenTelemetry span attributes used in the TA Bot service.

## Overview

Span attributes provide business context to traces, enabling better observability and debugging. All span attributes follow a consistent dot-notation naming convention to group related attributes logically.

## Naming Convention

### Dot Notation

Use dot notation to group related attributes:

- `strategy.name` - Strategy identifier
- `signal.type` - Signal action (buy/sell/hold/close)
- `signal.strength` - Signal strength level (weak/medium/strong/extreme)
- `signal.confidence` - Signal confidence score (0.0-1.0)
- `order.side` - Order side (buy/sell)
- `order.quantity` - Order quantity

### Business Context Attributes

#### Signal Analysis Spans

**`analyze_candles` span:**
- `symbol` - Trading symbol (e.g., "BTCUSDT")
- `timeframe` - Analysis timeframe (e.g., "15m", "1h")
- `candle_count` - Number of candles analyzed
- `current_price` - Current market price
- `strategies_count` - Number of strategies executed

**`run_strategy` span:**
- `strategy.name` - Strategy identifier (e.g., "momentum_pulse")
- `symbol` - Trading symbol
- `timeframe` - Analysis timeframe
- `current_price` - Current market price
- `signal_generated` - Boolean indicating if signal was generated
- `signal.type` - Signal action (buy/sell/hold/close)
- `signal.strength` - Signal strength (weak/medium/strong/extreme)
- `signal.confidence` - Signal confidence score (0.0-1.0)

#### Technical Indicator Spans

**`calculate_rsi` span:**
- `period` - RSI period
- `data_points` - Number of data points
- `rsi_value` - Calculated RSI value

**`calculate_macd` span:**
- `fast` - Fast EMA period
- `slow` - Slow EMA period
- `signal` - Signal line period
- `data_points` - Number of data points

## Examples

### Signal Generation

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("run_strategy") as span:
    # Business context attributes
    span.set_attribute("strategy.name", "momentum_pulse")
    span.set_attribute("symbol", "BTCUSDT")
    span.set_attribute("timeframe", "15m")
    span.set_attribute("current_price", 50000.0)

    # Signal attributes (set after signal is generated)
    if signal:
        span.set_attribute("signal.type", signal.action)
        span.set_attribute("signal.strength", signal.strength.value)
        span.set_attribute("signal.confidence", signal.confidence)
```

### Candle Analysis

```python
with tracer.start_as_current_span("analyze_candles") as span:
    span.set_attribute("symbol", "BTCUSDT")
    span.set_attribute("timeframe", "15m")
    span.set_attribute("candle_count", len(df))
    span.set_attribute("current_price", current_price)
```

## Benefits

1. **Consistency**: All attributes follow the same naming pattern
2. **Grouping**: Related attributes are logically grouped (e.g., `signal.*`, `order.*`)
3. **Searchability**: Easy to filter and search traces by attribute groups
4. **Documentation**: Clear convention makes it easy to understand what attributes are available

## Verification

To verify attributes in Grafana:

1. Open Grafana and navigate to Tempo/Tracing
2. Search for traces with `service.name="ta-bot"`
3. Expand spans to view attributes
4. Filter by attribute groups: `signal.type`, `strategy.name`, etc.

## Related Documentation

- [Architecture Documentation](ARCHITECTURE.md)
- [Monitoring Guide](MONITORING.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
