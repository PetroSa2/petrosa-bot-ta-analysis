# TA Bot Business Metrics Verification Guide

**Purpose**: Step-by-step guide to verify TA Bot business metrics are functioning correctly in production.

**Related**: Issue #108, PR #106 (metrics implementation)

---

## Prerequisites

- AWS SSO session authenticated (`aws sso login`)
- Kubernetes access to production cluster
- `kubectl` configured with correct context
- `jq` installed for JSON parsing

---

## Quick Verification Script

Run this script to verify all metrics at once:

```bash
#!/bin/bash
# File: scripts/verify-metrics.sh

set -e

echo "🔍 TA Bot Business Metrics Verification"
echo "========================================"
echo ""

# 1. Check TA Bot is running
echo "1️⃣ Checking TA Bot deployment..."
kubectl get pods -n petrosa-apps -l app=ta-bot --field-selector=status.phase=Running | grep -q "ta-bot" && \
  echo "   ✅ TA Bot is running" || \
  (echo "   ❌ TA Bot is not running" && exit 1)

# 2. Get TA Bot pod name
TA_BOT_POD=$(kubectl get pods -n petrosa-apps -l app=ta-bot --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}')
echo "   📦 Pod: $TA_BOT_POD"
echo ""

# 3. Verify metrics endpoint is accessible
echo "2️⃣ Checking metrics endpoint..."
kubectl exec -n petrosa-apps "$TA_BOT_POD" -- curl -s http://localhost:8080/metrics > /tmp/ta-bot-metrics.txt
if [ $? -eq 0 ]; then
  echo "   ✅ Metrics endpoint accessible"
else
  echo "   ❌ Cannot access metrics endpoint"
  exit 1
fi
echo ""

# 4. Verify each metric exists
echo "3️⃣ Verifying individual metrics..."
METRICS=(
  "ta_bot_signals_generated_total"
  "ta_bot_signal_processing_duration"
  "ta_bot_strategies_run_total"
  "ta_bot_strategy_executions_total"
  "ta_bot_config_changes_total"
)

for metric in "${METRICS[@]}"; do
  if grep -q "^${metric}" /tmp/ta-bot-metrics.txt; then
    echo "   ✅ $metric"
  else
    echo "   ❌ $metric NOT FOUND"
    exit 1
  fi
done
echo ""

# 5. Display current metric values
echo "4️⃣ Current Metric Values:"
echo ""
for metric in "${METRICS[@]}"; do
  echo "📊 $metric:"
  grep "^${metric}" /tmp/ta-bot-metrics.txt | head -5
  echo ""
done

# 6. Verify metrics are being scraped by Prometheus
echo "5️⃣ Checking Prometheus scraping..."
PROMETHEUS_POD=$(kubectl get pods -n monitoring -l app=prometheus -o jsonpath='{.items[0].metadata.name}')

for metric in "${METRICS[@]}"; do
  result=$(kubectl exec -n monitoring "$PROMETHEUS_POD" -- \
    wget -q -O- "http://localhost:9090/api/v1/query?query=${metric}" | \
    jq -r '.data.result | length')

  if [ "$result" -gt 0 ]; then
    echo "   ✅ $metric (found $result series)"
  else
    echo "   ⚠️  $metric (no data in Prometheus yet)"
  fi
done
echo ""

# 7. Test metric updates
echo "6️⃣ Testing metric updates..."
echo "   Triggering test analysis..."

# Get initial value
INITIAL_COUNT=$(grep "^ta_bot_strategies_run_total" /tmp/ta-bot-metrics.txt | grep 'symbol="BTCUSDT"' | awk '{print $2}' | head -1)
echo "   Initial count: ${INITIAL_COUNT:-0}"

# Trigger analysis (if health endpoint exists)
kubectl exec -n petrosa-apps "$TA_BOT_POD" -- \
  curl -s -X POST http://localhost:8080/health 2>/dev/null || \
  echo "   ℹ️  No test endpoint available - manual testing required"

# Wait for metric update
sleep 5

# Check updated value
kubectl exec -n petrosa-apps "$TA_BOT_POD" -- curl -s http://localhost:8080/metrics > /tmp/ta-bot-metrics-updated.txt
UPDATED_COUNT=$(grep "^ta_bot_strategies_run_total" /tmp/ta-bot-metrics-updated.txt | grep 'symbol="BTCUSDT"' | awk '{print $2}' | head -1)
echo "   Updated count: ${UPDATED_COUNT:-0}"

if [ "${UPDATED_COUNT:-0}" -gt "${INITIAL_COUNT:-0}" ]; then
  echo "   ✅ Metrics are updating"
else
  echo "   ⚠️  Metrics may not be updating (wait for next signal)"
fi
echo ""

echo "✅ Verification Complete!"
echo ""
echo "Next steps:"
echo "  1. Import Grafana dashboard from dashboards/ta-bot-business-metrics.json"
echo "  2. Document baseline values in docs/METRICS_BASELINE.md"
echo "  3. Capture dashboard screenshots"
```

---

## Manual Verification Steps

### Step 1: Verify TA Bot is Running

```bash
# Check deployment status
kubectl get deployment ta-bot -n petrosa-apps

# Check pod status
kubectl get pods -n petrosa-apps -l app=ta-bot

# Expected output: At least one pod in "Running" state
```

### Step 2: Access Metrics Endpoint

```bash
# Get pod name
TA_BOT_POD=$(kubectl get pods -n petrosa-apps -l app=ta-bot --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}')

# Fetch metrics
kubectl exec -n petrosa-apps "$TA_BOT_POD" -- curl -s http://localhost:8080/metrics > /tmp/ta-bot-metrics.txt

# View metrics
cat /tmp/ta-bot-metrics.txt | grep "^ta_bot"
```

### Step 3: Verify Each Metric

#### 3.1 Signal Generation Counter

```bash
# Check metric exists
grep "ta_bot_signals_generated_total" /tmp/ta-bot-metrics.txt

# Expected format:
# ta_bot_signals_generated_total{action="buy",strategy="rsi_oversold",symbol="BTCUSDT"} 15
# ta_bot_signals_generated_total{action="sell",strategy="macd_crossover",symbol="ETHUSDT"} 8
```

**Acceptance Criteria**:
- ✅ Metric exists
- ✅ Has labels: `action`, `strategy`, `symbol`
- ✅ Counter values are reasonable (> 0 for active strategies)

#### 3.2 Signal Processing Duration

```bash
# Check histogram metric
grep "ta_bot_signal_processing_duration" /tmp/ta-bot-metrics.txt

# Expected format:
# ta_bot_signal_processing_duration_bucket{strategy="rsi_oversold",le="0.5"} 10
# ta_bot_signal_processing_duration_bucket{strategy="rsi_oversold",le="1.0"} 25
# ta_bot_signal_processing_duration_sum{strategy="rsi_oversold"} 42.5
# ta_bot_signal_processing_duration_count{strategy="rsi_oversold"} 30
```

**Acceptance Criteria**:
- ✅ Histogram buckets exist
- ✅ Has labels: `strategy`
- ✅ `_sum` and `_count` values present
- ✅ Average latency = sum/count is reasonable (< 5 seconds)

#### 3.3 Strategies Run Counter

```bash
# Check metric
grep "ta_bot_strategies_run_total" /tmp/ta-bot-metrics.txt

# Expected format:
# ta_bot_strategies_run_total{strategy="golden_trend_sync",symbol="BTCUSDT"} 120
```

**Acceptance Criteria**:
- ✅ Metric exists
- ✅ Has labels: `strategy`, `symbol`
- ✅ Values indicate strategies are being executed

#### 3.4 Strategy Executions Counter

```bash
# Check metric with status
grep "ta_bot_strategy_executions_total" /tmp/ta-bot-metrics.txt

# Expected format:
# ta_bot_strategy_executions_total{status="success",strategy="rsi_oversold"} 45
# ta_bot_strategy_executions_total{status="error",strategy="macd_crossover"} 2
```

**Acceptance Criteria**:
- ✅ Metric exists
- ✅ Has labels: `status`, `strategy`
- ✅ Both `success` and `error` statuses present
- ✅ Success rate > 95%

#### 3.5 Config Changes Counter

```bash
# Check metric
grep "ta_bot_config_changes_total" /tmp/ta-bot-metrics.txt

# Expected format (may be 0 if no recent config changes):
# ta_bot_config_changes_total{action="update",strategy="rsi_oversold"} 3
# ta_bot_config_changes_total{action="delete",strategy="old_strategy"} 1
```

**Acceptance Criteria**:
- ✅ Metric exists
- ✅ Has labels: `action`, `strategy`
- ✅ Increments when config is changed via API

### Step 4: Verify Prometheus Scraping

```bash
# Get Prometheus pod
PROMETHEUS_POD=$(kubectl get pods -n monitoring -l app=prometheus -o jsonpath='{.items[0].metadata.name}')

# Query Prometheus for TA Bot metrics
kubectl exec -n monitoring "$PROMETHEUS_POD" -- \
  wget -q -O- "http://localhost:9090/api/v1/query?query=ta_bot_signals_generated_total" | \
  jq '.data.result[0]'

# Expected output: JSON with metric data
```

**Acceptance Criteria**:
- ✅ Prometheus can query all 5 metrics
- ✅ Data exists for each metric
- ✅ Timestamps are recent (< 1 minute old)

### Step 5: Test Metric Updates

#### Test Signal Generation Counter

```bash
# Get current count
BEFORE=$(kubectl exec -n petrosa-apps "$TA_BOT_POD" -- \
  curl -s http://localhost:8080/metrics | \
  grep "ta_bot_signals_generated_total" | \
  awk '{sum+=$2} END {print sum}')

# Wait for next analysis cycle (check pod logs for timing)
sleep 60

# Get updated count
AFTER=$(kubectl exec -n petrosa-apps "$TA_BOT_POD" -- \
  curl -s http://localhost:8080/metrics | \
  grep "ta_bot_signals_generated_total" | \
  awk '{sum+=$2} END {print sum}')

echo "Before: $BEFORE, After: $AFTER, Difference: $((AFTER - BEFORE))"
```

**Expected**: Counter should increment if signals were generated.

#### Test Config Change Counter

```bash
# Note current count
BEFORE=$(kubectl exec -n petrosa-apps "$TA_BOT_POD" -- \
  curl -s http://localhost:8080/metrics | \
  grep "ta_bot_config_changes_total" | \
  awk '{sum+=$2} END {print sum}')

# Update strategy config via API (if management API exists)
# Example: Update RSI period
# curl -X PUT http://ta-bot:8080/api/v1/strategies/rsi/config \
#   -H "Content-Type: application/json" \
#   -d '{"period": 15}'

# Check updated count
AFTER=$(kubectl exec -n petrosa-apps "$TA_BOT_POD" -- \
  curl -s http://localhost:8080/metrics | \
  grep "ta_bot_config_changes_total" | \
  awk '{sum+=$2} END {print sum}')

echo "Config changes incremented: $((AFTER - BEFORE))"
```

### Step 6: Import Grafana Dashboard

```bash
# Get Grafana URL and credentials
GRAFANA_URL=$(kubectl get ingress grafana -n monitoring -o jsonpath='{.spec.rules[0].host}')
GRAFANA_ADMIN_PASS=$(kubectl get secret grafana-admin -n monitoring -o jsonpath='{.data.password}' | base64 --decode)

echo "Grafana URL: https://${GRAFANA_URL}"
echo "Username: admin"
echo "Password: ${GRAFANA_ADMIN_PASS}"

# Import dashboard via API (or manually via UI)
# Navigate to Dashboards > Import > Upload JSON file
# Select: dashboards/ta-bot-business-metrics.json
```

**Manual Steps**:
1. Login to Grafana
2. Navigate to **Dashboards** → **Import**
3. Upload `dashboards/ta-bot-business-metrics.json`
4. Select Prometheus data source
5. Click **Import**

**Verification**:
- ✅ Dashboard loads without errors
- ✅ All 8 panels show data
- ✅ Time series graphs display trends
- ✅ Current values match Prometheus queries

### Step 7: Document Baseline

Once metrics are verified, document current values in `METRICS_BASELINE.md`.

---

## Troubleshooting

### Metrics Not Found

**Symptom**: `grep` returns no results for metric

**Possible Causes**:
1. TA Bot not running
2. Metrics not initialized (no activity yet)
3. Wrong metrics endpoint

**Resolution**:
```bash
# Check pod logs for errors
kubectl logs -n petrosa-apps "$TA_BOT_POD" --tail=100

# Verify metrics endpoint
kubectl exec -n petrosa-apps "$TA_BOT_POD" -- curl -s http://localhost:8080/metrics | head -20
```

### Prometheus Not Scraping

**Symptom**: Metrics exist in pod but not in Prometheus

**Possible Causes**:
1. ServiceMonitor not configured
2. Prometheus scrape config missing
3. Network policy blocking scraping

**Resolution**:
```bash
# Check if ServiceMonitor exists
kubectl get servicemonitor ta-bot -n petrosa-apps

# Check Prometheus targets
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# Visit: http://localhost:9090/targets
# Look for ta-bot target and check status
```

### Dashboard Shows "No Data"

**Possible Causes**:
1. Prometheus not scraping (see above)
2. Wrong time range selected
3. Metrics recently deployed (no historical data)

**Resolution**:
1. Verify Prometheus has data (Step 4)
2. Set dashboard time range to "Last 1 hour"
3. Wait for scrape interval (default 30 seconds)
4. Refresh dashboard

### Metrics Not Updating

**Symptom**: Counter values stay the same

**Possible Causes**:
1. TA Bot not analyzing (no market data)
2. Strategies disabled
3. No signals being generated

**Resolution**:
```bash
# Check TA Bot is actively processing
kubectl logs -n petrosa-apps "$TA_BOT_POD" --tail=50 | grep -i "signal\|strategy\|analysis"

# Check if strategies are enabled
# (view strategy config in MongoDB or via API)
```

---

## Success Criteria

All items must be checked before considering verification complete:

- [ ] All 5 metrics exist in `/metrics` endpoint
- [ ] Metrics have correct labels
- [ ] Prometheus is successfully scraping metrics
- [ ] Grafana dashboard imports without errors
- [ ] All 8 dashboard panels show data
- [ ] Signal counter increments during observation period
- [ ] Processing latency histogram shows distribution
- [ ] Strategy execution counter tracks success/error
- [ ] Config change counter can be tested
- [ ] Baseline values documented in `METRICS_BASELINE.md`
- [ ] Dashboard screenshots captured
- [ ] Verification runbook tested and validated

---

## Next Steps

After verification:
1. ✅ Update `docs/RUNBOOK.md` with metrics verification section
2. ✅ Create `docs/METRICS_BASELINE.md` with current values
3. ✅ Capture dashboard screenshots for documentation
4. ✅ Close issue #108
