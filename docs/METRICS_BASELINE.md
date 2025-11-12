# TA Bot Business Metrics Baseline

**Purpose**: Document baseline metric values for future comparison and anomaly detection.

**Captured**: *(To be filled after verification)*

**Environment**: Production (petrosa-apps namespace)

**Related**: Issue #108, PR #106

---

## Overview

This document captures baseline values for TA Bot business metrics to establish normal operating parameters. These values serve as:
- **Performance benchmarks** for future optimization efforts
- **Anomaly detection thresholds** for alerting
- **Capacity planning** for scaling decisions
- **Regression testing** baseline after deployments

---

## Metric 1: Signal Generation

**Metric**: `ta_bot_signals_generated_total`

**Description**: Total number of trading signals generated, labeled by action, strategy, and symbol.

### Current Values (To Be Filled)

```
# Example format:
Total signals (24h): ___
Total signals (7d): ___

By Action:
  - BUY signals: ___ (___%)
  - SELL signals: ___ (___%)
  - CLOSE_LONG signals: ___ (___%)
  - CLOSE_SHORT signals: ___ (___%)

By Strategy (Top 5):
  1. golden_trend_sync: ___ signals (___%)
  2. rsi_oversold: ___ signals (___%)
  3. macd_crossover: ___ signals (___%)
  4. bollinger_breakout: ___ signals (___%)
  5. momentum_pulse: ___ signals (___%)

By Symbol (Top 5):
  1. BTCUSDT: ___ signals
  2. ETHUSDT: ___ signals
  3. BNBUSDT: ___ signals
  4. ADAUSDT: ___ signals
  5. SOLUSDT: ___ signals

Average Rate:
  - Signals per hour: ~___
  - Signals per day: ~___
```

### Sample Prometheus Query

```promql
# Total signals in last 24h
sum(increase(ta_bot_signals_generated_total[24h]))

# By action
sum by (action) (increase(ta_bot_signals_generated_total[24h]))

# By strategy (top 5)
topk(5, sum by (strategy) (increase(ta_bot_signals_generated_total[24h])))

# By symbol (top 5)
topk(5, sum by (symbol) (increase(ta_bot_signals_generated_total[24h])))

# Signals per hour (average over 24h)
rate(ta_bot_signals_generated_total[24h]) * 3600
```

---

## Metric 2: Signal Processing Duration

**Metric**: `ta_bot_signal_processing_duration`

**Description**: Histogram of time taken to process each signal, labeled by strategy.

### Current Values (To Be Filled)

```
# Overall latency percentiles:
p50 (median): ___ ms
p75: ___ ms
p90: ___ ms
p95: ___ ms
p99: ___ ms
p99.9: ___ ms

# By strategy (Top 5 slowest):
1. ___: p95 = ___ ms
2. ___: p95 = ___ ms
3. ___: p95 = ___ ms
4. ___: p95 = ___ ms
5. ___: p95 = ___ ms

# Average processing time: ___ ms
```

### Sample Prometheus Query

```promql
# p50 latency (median)
histogram_quantile(0.50, sum(rate(ta_bot_signal_processing_duration_bucket[5m])) by (le))

# p95 latency
histogram_quantile(0.95, sum(rate(ta_bot_signal_processing_duration_bucket[5m])) by (le))

# p99 latency
histogram_quantile(0.99, sum(rate(ta_bot_signal_processing_duration_bucket[5m])) by (le))

# Average latency
sum(rate(ta_bot_signal_processing_duration_sum[5m])) / sum(rate(ta_bot_signal_processing_duration_count[5m]))

# By strategy (p95)
histogram_quantile(0.95, sum(rate(ta_bot_signal_processing_duration_bucket[5m])) by (le, strategy))
```

### Performance Targets

- ✅ **Acceptable**: p95 < 2000ms
- ⚠️ **Warning**: p95 between 2000-3000ms
- ❌ **Critical**: p95 > 3000ms

---

## Metric 3: Strategies Run

**Metric**: `ta_bot_strategies_run_total`

**Description**: Total number of strategy analysis runs, labeled by strategy and symbol.

### Current Values (To Be Filled)

```
# Total runs (24h): ___
# Total runs (7d): ___

# By strategy (Top 5 most active):
1. ___: ___ runs (___%)
2. ___: ___ runs (___%)
3. ___: ___ runs (___%)
4. ___: ___ runs (___%)
5. ___: ___ runs (___%)

# By symbol:
- BTCUSDT: ___ runs
- ETHUSDT: ___ runs
- (list all monitored symbols)

# Average runs per strategy per hour: ~___
```

### Sample Prometheus Query

```promql
# Total runs in last 24h
sum(increase(ta_bot_strategies_run_total[24h]))

# By strategy
sum by (strategy) (increase(ta_bot_strategies_run_total[24h]))

# By symbol
sum by (symbol) (increase(ta_bot_strategies_run_total[24h]))

# Runs per hour
rate(ta_bot_strategies_run_total[1h]) * 3600
```

---

## Metric 4: Strategy Executions

**Metric**: `ta_bot_strategy_executions_total`

**Description**: Total strategy executions with success/error status, labeled by status and strategy.

### Current Values (To Be Filled)

```
# Total executions (24h): ___
# Successful: ___ (___%)
# Failed: ___ (___%)

# Success Rate: ___%
# Error Rate: ___%

# By strategy (success rate):
1. ___: ___% success (___ total)
2. ___: ___% success (___ total)
3. ___: ___% success (___ total)

# Strategies with errors (if any):
- ___: ___ errors (error rate: ___%)
  - Common error types: ___

# Most reliable strategies (100% success rate):
- ___
- ___
```

### Sample Prometheus Query

```promql
# Total executions
sum(increase(ta_bot_strategy_executions_total[24h]))

# Success count
sum(increase(ta_bot_strategy_executions_total{status="success"}[24h]))

# Error count
sum(increase(ta_bot_strategy_executions_total{status="error"}[24h]))

# Success rate (%)
sum(increase(ta_bot_strategy_executions_total{status="success"}[24h])) /
sum(increase(ta_bot_strategy_executions_total[24h])) * 100

# By strategy
sum by (strategy, status) (increase(ta_bot_strategy_executions_total[24h]))
```

### Performance Targets

- ✅ **Acceptable**: Success rate > 98%
- ⚠️ **Warning**: Success rate between 95-98%
- ❌ **Critical**: Success rate < 95%

---

## Metric 5: Configuration Changes

**Metric**: `ta_bot_config_changes_total`

**Description**: Total configuration changes via runtime API, labeled by action and strategy.

### Current Values (To Be Filled)

```
# Total changes (24h): ___
# Total changes (7d): ___
# Total changes (30d): ___

# By action:
- create: ___ (___%)
- update: ___ (___%)
- delete: ___ (___%)

# By strategy (most frequently changed):
1. ___: ___ changes
2. ___: ___ changes
3. ___: ___ changes

# Average changes per day: ~___
# Peak change periods: ___
```

### Sample Prometheus Query

```promql
# Total changes in last 7 days
sum(increase(ta_bot_config_changes_total[7d]))

# By action
sum by (action) (increase(ta_bot_config_changes_total[7d]))

# By strategy
sum by (strategy) (increase(ta_bot_config_changes_total[7d]))

# Changes per day (average over 7d)
sum(increase(ta_bot_config_changes_total[7d])) / 7
```

---

## Operational Insights

### Signal Generation Patterns

*(To be filled after observation)*

```
Peak signal hours: ___
Quiet periods: ___
BUY/SELL ratio: ___
Most active strategies: ___
Most volatile symbols: ___
```

### Performance Characteristics

```
Average latency trend: ___
Latency spikes observed: ___
Strategies causing delays: ___
Resource utilization correlation: ___
```

### Reliability Metrics

```
Overall uptime: ___%
Strategy error patterns: ___
Common failure modes: ___
Recovery time: ___
```

### Configuration Activity

```
Typical config change frequency: ___
Changes correlated with: ___
Most tuned strategies: ___
Config stability: ___
```

---

## Alert Thresholds (Recommended)

Based on baseline values, recommended Prometheus alert thresholds:

### Signal Generation Rate

```yaml
# Alert if signal rate drops significantly
- alert: TaBotLowSignalRate
  expr: rate(ta_bot_signals_generated_total[1h]) < (BASELINE * 0.5)
  for: 15m
  annotations:
    summary: "TA Bot signal generation rate is 50% below baseline"

# Alert if signal rate spikes (possible issue)
- alert: TaBotHighSignalRate
  expr: rate(ta_bot_signals_generated_total[1h]) > (BASELINE * 2.0)
  for: 15m
  annotations:
    summary: "TA Bot signal generation rate is 200% above baseline"
```

### Processing Latency

```yaml
# Alert if p95 latency exceeds 3 seconds
- alert: TaBotHighLatency
  expr: histogram_quantile(0.95, sum(rate(ta_bot_signal_processing_duration_bucket[5m])) by (le)) > 3.0
  for: 10m
  annotations:
    summary: "TA Bot p95 signal processing latency > 3s"
```

### Strategy Error Rate

```yaml
# Alert if error rate exceeds 5%
- alert: TaBotHighErrorRate
  expr: |
    sum(rate(ta_bot_strategy_executions_total{status="error"}[5m])) /
    sum(rate(ta_bot_strategy_executions_total[5m])) > 0.05
  for: 15m
  annotations:
    summary: "TA Bot strategy error rate > 5%"
```

---

## Verification Schedule

Baseline values should be:
- **Captured**: Within 1 week of metrics deployment
- **Reviewed**: Monthly to identify trends
- **Updated**: After major changes (new strategies, config tuning, infrastructure updates)

---

## Appendix: Data Collection Commands

```bash
# Collect all baseline data at once
./scripts/collect-baseline-metrics.sh > baseline-$(date +%Y%m%d).txt

# Export to CSV for analysis
./scripts/export-metrics-csv.sh > baseline-$(date +%Y%m%d).csv
```

---

## Notes

- Baseline values are environment-specific (production vs staging will differ)
- Values will evolve as strategies are tuned and system matures
- Keep historical baselines for trend analysis
- Use baselines for capacity planning and scaling decisions
