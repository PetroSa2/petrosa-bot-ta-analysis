#!/bin/bash
# TA Bot Business Metrics Baseline Collection Script
# Purpose: Collect current metric values from Prometheus for baseline documentation
# Usage: ./scripts/collect-baseline-metrics.sh [output-file]
#
# This script queries Prometheus for all TA Bot business metrics and outputs
# formatted data suitable for pasting into METRICS_BASELINE.md

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

OUTPUT_FILE="${1:-/tmp/baseline-metrics-$(date +%Y%m%d-%H%M%S).txt}"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📊 TA Bot Business Metrics Baseline Collection${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if Prometheus is available
if ! kubectl get pods -n monitoring -l app=prometheus &>/dev/null; then
  echo -e "${RED}❌ Prometheus not found in monitoring namespace${NC}"
  echo -e "${YELLOW}⚠️  Cannot collect baseline metrics without Prometheus${NC}"
  echo ""
  echo "Alternative: Use verify-metrics.sh to collect from pod metrics endpoint"
  exit 1
fi

PROMETHEUS_POD=$(kubectl get pods -n monitoring -l app=prometheus -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -z "$PROMETHEUS_POD" ]; then
  echo -e "${RED}❌ Prometheus pod not found${NC}"
  exit 1
fi

echo -e "${GREEN}✅ Found Prometheus pod: $PROMETHEUS_POD${NC}"
echo ""

# Function to URL-encode a string
url_encode() {
  local string="$1"
  python3 -c "import urllib.parse; print(urllib.parse.quote('$string'))" 2>/dev/null || echo "$string"
}

# Function to query Prometheus
query_prometheus() {
  local query="$1"
  local encoded_query
  encoded_query=$(url_encode "$query")
  kubectl exec -n monitoring "$PROMETHEUS_POD" -- \
    wget -q -O- --timeout=10 "http://localhost:9090/api/v1/query?query=${encoded_query}" 2>/dev/null | \
    jq -r '.data.result[] | "\(.metric | to_entries | map("\(.key)=\"\(.value)\"") | join(",")) \(.value[1])"' 2>/dev/null || echo ""
}

# Function to query Prometheus and get sum
query_sum() {
  local query="$1"
  local encoded_query
  encoded_query=$(url_encode "$query")
  kubectl exec -n monitoring "$PROMETHEUS_POD" -- \
    wget -q -O- --timeout=10 "http://localhost:9090/api/v1/query?query=${encoded_query}" 2>/dev/null | \
    jq -r '.data.result[0].value[1] // "0"' 2>/dev/null || echo "0"
}

# Start output file
cat > "$OUTPUT_FILE" << EOF
# TA Bot Business Metrics Baseline
# Collected: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
# Environment: Production (petrosa-apps namespace)
# Prometheus Pod: $PROMETHEUS_POD

---

## Metric 1: Signal Generation

**Metric**: \`ta_bot_signals_generated_total\`

### Current Values

EOF

echo -e "${BLUE}📊 Collecting Signal Generation metrics...${NC}"

# Total signals in last 24h
TOTAL_24H=$(query_sum "sum(increase(ta_bot_signals_generated_total[24h]))")
echo "Total signals (24h): $TOTAL_24H" >> "$OUTPUT_FILE"

# Total signals in last 7d
TOTAL_7D=$(query_sum "sum(increase(ta_bot_signals_generated_total[7d]))")
echo "Total signals (7d): $TOTAL_7D" >> "$OUTPUT_FILE"

# By action
echo "" >> "$OUTPUT_FILE"
echo "By Action:" >> "$OUTPUT_FILE"
ACTIONS=$(query_prometheus "sum by (action) (increase(ta_bot_signals_generated_total[24h]))")
if [ -n "$ACTIONS" ]; then
  echo "$ACTIONS" | while IFS= read -r line; do
    ACTION=$(echo "$line" | grep -oP 'action="\K[^"]+')
    COUNT=$(echo "$line" | awk '{print $NF}')
    if [ -n "$ACTION" ] && [ -n "$COUNT" ]; then
      if [ "$TOTAL_24H" != "0" ] && [ -n "$TOTAL_24H" ] && [ "$TOTAL_24H" != "null" ]; then
        PCT=$(awk "BEGIN {printf \"%.1f\", ($COUNT / $TOTAL_24H) * 100}" 2>/dev/null || echo "0")
      else
        PCT="0"
      fi
      echo "  - ${ACTION}: $COUNT (${PCT}%)" >> "$OUTPUT_FILE"
    fi
  done
else
  echo "  - (No data available)" >> "$OUTPUT_FILE"
fi

# By strategy (top 5)
echo "" >> "$OUTPUT_FILE"
echo "By Strategy (Top 5):" >> "$OUTPUT_FILE"
STRATEGIES=$(query_prometheus "topk(5, sum by (strategy) (increase(ta_bot_signals_generated_total[24h])))")
if [ -n "$STRATEGIES" ]; then
  RANK=1
  echo "$STRATEGIES" | head -5 | while IFS= read -r line; do
    STRATEGY=$(echo "$line" | grep -oP 'strategy="\K[^"]+')
    COUNT=$(echo "$line" | awk '{print $NF}')
    if [ -n "$STRATEGY" ] && [ -n "$COUNT" ]; then
      if [ "$TOTAL_24H" != "0" ] && [ -n "$TOTAL_24H" ] && [ "$TOTAL_24H" != "null" ]; then
        PCT=$(awk "BEGIN {printf \"%.1f\", ($COUNT / $TOTAL_24H) * 100}" 2>/dev/null || echo "0")
      else
        PCT="0"
      fi
      echo "$RANK. ${STRATEGY}: $COUNT signals (${PCT}%)" >> "$OUTPUT_FILE"
      RANK=$((RANK + 1))
    fi
  done
else
  echo "  (No data available)" >> "$OUTPUT_FILE"
fi

# By symbol (top 5)
echo "" >> "$OUTPUT_FILE"
echo "By Symbol (Top 5):" >> "$OUTPUT_FILE"
SYMBOLS=$(query_prometheus "topk(5, sum by (symbol) (increase(ta_bot_signals_generated_total[24h])))")
if [ -n "$SYMBOLS" ]; then
  RANK=1
  echo "$SYMBOLS" | head -5 | while IFS= read -r line; do
    SYMBOL=$(echo "$line" | grep -oP 'symbol="\K[^"]+')
    COUNT=$(echo "$line" | awk '{print $NF}')
    if [ -n "$SYMBOL" ] && [ -n "$COUNT" ]; then
      echo "$RANK. ${SYMBOL}: $COUNT signals" >> "$OUTPUT_FILE"
      RANK=$((RANK + 1))
    fi
  done
else
  echo "  (No data available)" >> "$OUTPUT_FILE"
fi

# Average rate
if [ "$TOTAL_24H" != "0" ] && [ -n "$TOTAL_24H" ] && [ "$TOTAL_24H" != "null" ]; then
  SIGNALS_PER_HOUR=$(awk "BEGIN {printf \"%.1f\", $TOTAL_24H / 24}" 2>/dev/null || echo "0")
else
  SIGNALS_PER_HOUR="0"
fi
SIGNALS_PER_DAY="$TOTAL_24H"
echo "" >> "$OUTPUT_FILE"
echo "Average Rate:" >> "$OUTPUT_FILE"
echo "  - Signals per hour: ~$SIGNALS_PER_HOUR" >> "$OUTPUT_FILE"
echo "  - Signals per day: ~$SIGNALS_PER_DAY" >> "$OUTPUT_FILE"

# Metric 2: Processing Duration
cat >> "$OUTPUT_FILE" << EOF

---

## Metric 2: Signal Processing Duration

**Metric**: \`ta_bot_signal_processing_duration\`

### Current Values

EOF

echo -e "${BLUE}📊 Collecting Processing Duration metrics...${NC}"

# Calculate percentiles
P50=$(query_sum "histogram_quantile(0.50, sum(rate(ta_bot_signal_processing_duration_bucket[5m])) by (le))")
P75=$(query_sum "histogram_quantile(0.75, sum(rate(ta_bot_signal_processing_duration_bucket[5m])) by (le))")
P90=$(query_sum "histogram_quantile(0.90, sum(rate(ta_bot_signal_processing_duration_bucket[5m])) by (le))")
P95=$(query_sum "histogram_quantile(0.95, sum(rate(ta_bot_signal_processing_duration_bucket[5m])) by (le))")
P99=$(query_sum "histogram_quantile(0.99, sum(rate(ta_bot_signal_processing_duration_bucket[5m])) by (le))")
P999=$(query_sum "histogram_quantile(0.999, sum(rate(ta_bot_signal_processing_duration_bucket[5m])) by (le))")

echo "Overall latency percentiles:" >> "$OUTPUT_FILE"
echo "p50 (median): ${P50} ms" >> "$OUTPUT_FILE"
echo "p75: ${P75} ms" >> "$OUTPUT_FILE"
echo "p90: ${P90} ms" >> "$OUTPUT_FILE"
echo "p95: ${P95} ms" >> "$OUTPUT_FILE"
echo "p99: ${P99} ms" >> "$OUTPUT_FILE"
echo "p99.9: ${P999} ms" >> "$OUTPUT_FILE"

# Average
AVG_LATENCY=$(query_sum "sum(rate(ta_bot_signal_processing_duration_sum[5m])) / sum(rate(ta_bot_signal_processing_duration_count[5m]))")
echo "" >> "$OUTPUT_FILE"
echo "Average processing time: ${AVG_LATENCY} ms" >> "$OUTPUT_FILE"

# Metric 3: Strategies Run
cat >> "$OUTPUT_FILE" << EOF

---

## Metric 3: Strategies Run

**Metric**: \`ta_bot_strategies_run_total\`

### Current Values

EOF

echo -e "${BLUE}📊 Collecting Strategies Run metrics...${NC}"

TOTAL_RUNS_24H=$(query_sum "sum(increase(ta_bot_strategies_run_total[24h]))")
TOTAL_RUNS_7D=$(query_sum "sum(increase(ta_bot_strategies_run_total[7d]))")

echo "Total runs (24h): $TOTAL_RUNS_24H" >> "$OUTPUT_FILE"
echo "Total runs (7d): $TOTAL_RUNS_7D" >> "$OUTPUT_FILE"

# Metric 4: Strategy Executions
cat >> "$OUTPUT_FILE" << EOF

---

## Metric 4: Strategy Executions

**Metric**: \`ta_bot_strategy_executions_total\`

### Current Values

EOF

echo -e "${BLUE}📊 Collecting Strategy Executions metrics...${NC}"

TOTAL_EXEC_24H=$(query_sum "sum(increase(ta_bot_strategy_executions_total[24h]))")
SUCCESS_EXEC=$(query_sum "sum(increase(ta_bot_strategy_executions_total{status=\"success\"}[24h]))")
ERROR_EXEC=$(query_sum "sum(increase(ta_bot_strategy_executions_total{status=\"error\"}[24h]))")

if [ "$TOTAL_EXEC_24H" != "0" ] && [ -n "$TOTAL_EXEC_24H" ]; then
  SUCCESS_RATE=$(awk "BEGIN {printf \"%.2f\", ($SUCCESS_EXEC / $TOTAL_EXEC_24H) * 100}" 2>/dev/null || echo "0")
  ERROR_RATE=$(awk "BEGIN {printf \"%.2f\", ($ERROR_EXEC / $TOTAL_EXEC_24H) * 100}" 2>/dev/null || echo "0")
else
  SUCCESS_RATE="0"
  ERROR_RATE="0"
fi

echo "Total executions (24h): $TOTAL_EXEC_24H" >> "$OUTPUT_FILE"
echo "Successful: $SUCCESS_EXEC (${SUCCESS_RATE}%)" >> "$OUTPUT_FILE"
echo "Failed: $ERROR_EXEC (${ERROR_RATE}%)" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "Success Rate: ${SUCCESS_RATE}%" >> "$OUTPUT_FILE"
echo "Error Rate: ${ERROR_RATE}%" >> "$OUTPUT_FILE"

# Metric 5: Config Changes
cat >> "$OUTPUT_FILE" << EOF

---

## Metric 5: Configuration Changes

**Metric**: \`ta_bot_config_changes_total\`

### Current Values

EOF

echo -e "${BLUE}📊 Collecting Config Changes metrics...${NC}"

TOTAL_CHANGES_24H=$(query_sum "sum(increase(ta_bot_config_changes_total[24h]))")
TOTAL_CHANGES_7D=$(query_sum "sum(increase(ta_bot_config_changes_total[7d]))")
TOTAL_CHANGES_30D=$(query_sum "sum(increase(ta_bot_config_changes_total[30d]))")

echo "Total changes (24h): $TOTAL_CHANGES_24H" >> "$OUTPUT_FILE"
echo "Total changes (7d): $TOTAL_CHANGES_7D" >> "$OUTPUT_FILE"
echo "Total changes (30d): $TOTAL_CHANGES_30D" >> "$OUTPUT_FILE"

if [ "$TOTAL_CHANGES_7D" != "0" ] && [ -n "$TOTAL_CHANGES_7D" ]; then
  AVG_CHANGES_PER_DAY=$(awk "BEGIN {printf \"%.1f\", $TOTAL_CHANGES_7D / 7}" 2>/dev/null || echo "0")
  echo "" >> "$OUTPUT_FILE"
  echo "Average changes per day: ~$AVG_CHANGES_PER_DAY" >> "$OUTPUT_FILE"
fi

# Summary
cat >> "$OUTPUT_FILE" << EOF

---

## Summary

**Collection Date**: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
**Prometheus Pod**: $PROMETHEUS_POD
**Namespace**: monitoring

**Next Steps**:
1. Review collected values above
2. Copy relevant sections to docs/METRICS_BASELINE.md
3. Update "Captured" date in METRICS_BASELINE.md
4. Add operational insights based on collected data
5. Set up alert thresholds based on baseline values

EOF

echo ""
echo -e "${GREEN}✅ Baseline metrics collected successfully!${NC}"
echo -e "${BLUE}📄 Output saved to: $OUTPUT_FILE${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Review the collected data in $OUTPUT_FILE"
echo "  2. Copy relevant sections to docs/METRICS_BASELINE.md"
echo "  3. Update the 'Captured' date in METRICS_BASELINE.md"
echo "  4. Add any operational insights or notes"
echo ""
