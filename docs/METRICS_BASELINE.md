# TA Bot Business Metrics Baseline

**Last Updated**: Pending first verification (Issue #108)
**Version Deployed**: v1.0.68+ (with metrics from PR #106)
**Capture Date**: TBD

---

## Overview

This document captures baseline metric values for the TA Bot to enable:
- Performance regression detection
- Anomaly identification
- Capacity planning
- Alert threshold validation

**How to Update**: Re-run verification steps from `docs/RUNBOOK.md` after significant changes.

---

## Signal Generation Metrics

### Overall Signal Production

**Metric**: `ta_bot_signals_generated_total`

| Timeframe | Signals/Hour | Signals/Day | Top Strategy | BUY/SELL Ratio |
|-----------|--------------|-------------|--------------|----------------|
| 15m | TBD | TBD | TBD | TBD |
| 1h | TBD | TBD | TBD | TBD |
| Overall | TBD | TBD | TBD | TBD |

**Query to Capture**:
```promql
# Signals per hour (last 24h average)
rate(ta_bot_signals_generated_total[24h]) * 3600

# By strategy
sum by (strategy) (increase(ta_bot_signals_generated_total[24h]))

# BUY vs SELL distribution
sum by (action) (increase(ta_bot_signals_generated_total[24h]))
```

### Top Performing Strategies

| Rank | Strategy | Signals/Day | % of Total | Avg Confidence |
|------|----------|-------------|------------|----------------|
| 1 | TBD | TBD | TBD | TBD |
| 2 | TBD | TBD | TBD | TBD |
| 3 | TBD | TBD | TBD | TBD |
| 4 | TBD | TBD | TBD | TBD |
| 5 | TBD | TBD | TBD | TBD |

**Query to Capture**:
```promql
# Top 10 strategies by signal count
topk(10, sum by (strategy) (increase(ta_bot_signals_generated_total[24h])))
```

---

## Processing Performance Metrics

### Signal Processing Latency

**Metric**: `ta_bot_signal_processing_duration`

| Percentile | Latency (ms) | Expected Range | Alert Threshold |
|------------|--------------|----------------|-----------------|
| p50 | TBD | 500-1500ms | N/A |
| p95 | TBD | 1500-3000ms | N/A |
| p99 | TBD | 2500-4500ms | >5000ms for 10min |
| max | TBD | <8000ms | N/A |

**Query to Capture**:
```promql
# p50 latency
histogram_quantile(0.50, rate(ta_bot_signal_processing_duration_bucket[5m]))

# p95 latency
histogram_quantile(0.95, rate(ta_bot_signal_processing_duration_bucket[5m]))

# p99 latency
histogram_quantile(0.99, rate(ta_bot_signal_processing_duration_bucket[5m]))
```

### By Symbol/Timeframe

| Symbol | Timeframe | p50 | p95 | p99 |
|--------|-----------|-----|-----|-----|
| BTCUSDT | 15m | TBD | TBD | TBD |
| BTCUSDT | 1h | TBD | TBD | TBD |
| ETHUSDT | 15m | TBD | TBD | TBD |
| ETHUSDT | 1h | TBD | TBD | TBD |
| ADAUSDT | 15m | TBD | TBD | TBD |
| ADAUSDT | 1h | TBD | TBD | TBD |

**Query to Capture**:
```promql
# Latency by symbol and timeframe
histogram_quantile(0.99, rate(ta_bot_signal_processing_duration_bucket[5m])) by (symbol, timeframe)
```

---

## Strategy Execution Metrics

### Execution Success Rate

**Metric**: `ta_bot_strategy_executions_total`

| Category | Value | Expected Range | Alert Threshold |
|----------|-------|----------------|-----------------|
| Total Executions/Hour | TBD | 100-500 | N/A |
| Success Rate | TBD | >95% | <95% for 5min |
| Error Rate | TBD | <5% | >5% for 5min |
| Most Reliable Strategy | TBD | 100% success | N/A |
| Most Errors | TBD | N/A | N/A |

**Query to Capture**:
```promql
# Overall success rate
sum(rate(ta_bot_strategy_executions_total{status="success"}[5m]))
/
sum(rate(ta_bot_strategy_executions_total[5m]))

# Error rate
sum(rate(ta_bot_strategy_executions_total{status="error"}[5m]))
/
sum(rate(ta_bot_strategy_executions_total[5m]))

# Executions per hour
sum(rate(ta_bot_strategy_executions_total[1h])) * 3600
```

### Strategy Execution Breakdown

| Strategy | Executions/Hour | Success Rate | Signal Hit Rate |
|----------|-----------------|--------------|-----------------|
| momentum_pulse | TBD | TBD | TBD |
| golden_trend_sync | TBD | TBD | TBD |
| band_fade_reversal | TBD | TBD | TBD |
| range_break_pop | TBD | TBD | TBD |
| divergence_trap | TBD | TBD | TBD |

**Query to Capture**:
```promql
# Success rate by strategy
sum by (strategy) (rate(ta_bot_strategy_executions_total{status="success"}[1h]))
/
sum by (strategy) (rate(ta_bot_strategy_executions_total[1h]))

# Signal generation rate (signals / executions)
sum by (strategy) (rate(ta_bot_strategy_executions_total{signal_generated="yes"}[1h]))
/
sum by (strategy) (rate(ta_bot_strategy_executions_total[1h]))
```

---

## Strategies Run Metrics

### Strategies Per Analysis Cycle

**Metric**: `ta_bot_strategies_run_total`

| Metric | Value | Expected Range | Notes |
|--------|-------|----------------|-------|
| Avg Strategies/Cycle | TBD | 28 (all enabled) | Depends on enabled config |
| Rate (cycles/hour) | TBD | 50-200 | Depends on analysis frequency |

**Query to Capture**:
```promql
# Strategies run per cycle
rate(ta_bot_strategies_run_total[5m])

# By symbol/timeframe
rate(ta_bot_strategies_run_total[5m]) by (symbol, timeframe)
```

---

## Configuration Change Metrics

### Configuration Activity

**Metric**: `ta_bot_config_changes_total`

| Period | Changes | Most Changed Strategy | Change Types |
|--------|---------|----------------------|--------------|
| Last 24h | TBD | TBD | create/update/delete |
| Last 7 days | TBD | TBD | TBD |
| Last 30 days | TBD | TBD | TBD |

**Query to Capture**:
```promql
# Changes in last 24h
increase(ta_bot_config_changes_total[24h])

# By action type
sum by (action) (increase(ta_bot_config_changes_total[24h]))

# Most changed strategy
topk(5, sum by (strategy_id) (increase(ta_bot_config_changes_total[7d])))
```

---

## Resource Utilization Baseline

### Pod Resource Usage

| Metric | Per Pod | Total (3 replicas) | Limit | Utilization % |
|--------|---------|-------------------|-------|---------------|
| CPU (avg) | TBD | TBD | TBD | TBD |
| CPU (peak) | TBD | TBD | TBD | TBD |
| Memory (avg) | TBD | TBD | TBD | TBD |
| Memory (peak) | TBD | TBD | TBD | TBD |

**Command to Capture**:
```bash
kubectl --kubeconfig=k8s/kubeconfig.yaml top pods -n petrosa-apps -l app=petrosa-ta-bot
```

---

## Verification Checklist

Use this checklist when updating baseline metrics:

- [ ] All 5 custom metrics visible in Prometheus
- [ ] Grafana dashboard shows data in all 8 panels
- [ ] Signal generation rate aligns with expected trading activity
- [ ] Processing latency within acceptable ranges
- [ ] Strategy execution success rate >95%
- [ ] Configuration change frequency documented
- [ ] Resource utilization within limits
- [ ] No errors in TA Bot logs
- [ ] All 3 replicas healthy
- [ ] Leader election functioning (1 leader, 2 followers)

---

## Baseline Capture Commands

**Complete verification script**:

```bash
#!/bin/bash
# Run this script to capture all baseline metrics

echo "=== TA Bot Metrics Baseline Capture ==="
echo "Date: $(date)"
echo ""

# Check pods
echo "1. Pod Status:"
kubectl --kubeconfig=k8s/kubeconfig.yaml get pods -n petrosa-apps -l app=petrosa-ta-bot
echo ""

# Query Prometheus for all metrics
echo "2. Signal Generation (24h):"
SIGNALS=$(curl -s "http://prometheus:9090/api/v1/query?query=sum(increase(ta_bot_signals_generated_total[24h]))" | jq -r '.data.result[0].value[1] // "N/A"')
echo "  Total: $SIGNALS"
echo ""

echo "3. Top 5 Strategies:"
curl -s "http://prometheus:9090/api/v1/query?query=topk(5, sum by (strategy) (increase(ta_bot_signals_generated_total[24h])))" | jq -r '.data.result[]? | "\(.metric.strategy): \(.value[1])"' || echo "  No data available"
echo ""

echo "4. Processing Latency:"
for quantile in 0.50 0.95 0.99; do
  latency=$(curl -s "http://prometheus:9090/api/v1/query?query=histogram_quantile($quantile, rate(ta_bot_signal_processing_duration_bucket[5m]))" | jq -r '.data.result[0].value[1] // "N/A"')
  p_label=$(printf "%.0f" $(echo "$quantile * 100" | bc))
  echo "  p${p_label}: ${latency}ms"
done
echo ""

echo "5. Strategy Success Rate:"
SUCCESS_RATE=$(curl -s "http://prometheus:9090/api/v1/query?query=sum(rate(ta_bot_strategy_executions_total{status='success'}[5m])) / sum(rate(ta_bot_strategy_executions_total[5m]))" | jq -r '.data.result[0].value[1] // "N/A"')
if [ "$SUCCESS_RATE" != "N/A" ]; then
  printf "  %.2f%%\n" $(echo "$SUCCESS_RATE * 100" | bc)
else
  echo "  N/A"
fi
echo ""

echo "6. Config Changes (7d):"
CHANGES=$(curl -s "http://prometheus:9090/api/v1/query?query=sum(increase(ta_bot_config_changes_total[7d]))" | jq -r '.data.result[0].value[1] // "N/A"')
echo "  Total: $CHANGES"
echo ""

echo "=== Baseline Capture Complete ==="
echo ""
echo "Note: If values show 'N/A', metrics may not have data yet."
echo "  - Ensure TA Bot has been running for at least 15 minutes"
echo "  - Verify metrics are being scraped by Prometheus"
echo "  - Check that signals have been generated"
```

---

## Notes

- **First Verification**: Run after deploying v1.0.68+ with metrics
- **Update Frequency**: After significant changes (new strategies, config updates, scaling)
- **Anomaly Detection**: Compare current values to baseline to identify issues
- **Alert Tuning**: Use baseline p99 latency +20% for alert thresholds
- **Error Handling**: All queries use `// "N/A"` to handle missing data gracefully
