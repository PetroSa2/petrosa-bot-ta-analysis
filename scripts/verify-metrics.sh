#!/bin/bash
# TA Bot Business Metrics Verification Script
# Purpose: Automated verification of all business metrics in production
# Usage: ./scripts/verify-metrics.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🔍 TA Bot Business Metrics Verification${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Track verification results
VERIFICATION_PASSED=true
FAILED_CHECKS=()

# 1. Check TA Bot is running
echo -e "${BLUE}1️⃣  Checking TA Bot deployment...${NC}"
if kubectl get pods -n petrosa-apps -l app=ta-bot --field-selector=status.phase=Running | grep -q "ta-bot"; then
  echo -e "   ${GREEN}✅ TA Bot is running${NC}"
else
  echo -e "   ${RED}❌ TA Bot is not running${NC}"
  VERIFICATION_PASSED=false
  FAILED_CHECKS+=("TA Bot not running")
  exit 1
fi

# Get TA Bot pod name
TA_BOT_POD=$(kubectl get pods -n petrosa-apps -l app=ta-bot --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}')
echo -e "   ${BLUE}📦 Pod: $TA_BOT_POD${NC}"
echo ""

# 2. Verify metrics endpoint is accessible
echo -e "${BLUE}2️⃣  Checking metrics endpoint...${NC}"
if kubectl exec -n petrosa-apps "$TA_BOT_POD" -- curl -s --max-time 5 http://localhost:8080/metrics > /tmp/ta-bot-metrics.txt 2>/dev/null; then
  METRIC_COUNT=$(wc -l < /tmp/ta-bot-metrics.txt)
  echo -e "   ${GREEN}✅ Metrics endpoint accessible ($METRIC_COUNT lines)${NC}"
else
  echo -e "   ${RED}❌ Cannot access metrics endpoint${NC}"
  VERIFICATION_PASSED=false
  FAILED_CHECKS+=("Metrics endpoint not accessible")
  exit 1
fi
echo ""

# 3. Verify each metric exists
echo -e "${BLUE}3️⃣  Verifying individual metrics...${NC}"
METRICS=(
  "ta_bot_signals_generated_total"
  "ta_bot_signal_processing_duration"
  "ta_bot_strategies_run_total"
  "ta_bot_strategy_executions_total"
  "ta_bot_config_changes_total"
)

for metric in "${METRICS[@]}"; do
  if grep -q "^${metric}" /tmp/ta-bot-metrics.txt; then
    COUNT=$(grep -c "^${metric}" /tmp/ta-bot-metrics.txt)
    echo -e "   ${GREEN}✅ ${metric}${NC} (${COUNT} series)"
  else
    echo -e "   ${RED}❌ ${metric} NOT FOUND${NC}"
    VERIFICATION_PASSED=false
    FAILED_CHECKS+=("Metric ${metric} missing")
  fi
done
echo ""

# 4. Display current metric values
echo -e "${BLUE}4️⃣  Current Metric Values:${NC}"
echo ""

for metric in "${METRICS[@]}"; do
  echo -e "${YELLOW}📊 ${metric}:${NC}"
  if grep -q "^${metric}" /tmp/ta-bot-metrics.txt; then
    grep "^${metric}" /tmp/ta-bot-metrics.txt | head -5
  else
    echo "   (not found)"
  fi
  echo ""
done

# 5. Verify metrics are being scraped by Prometheus (if available)
echo -e "${BLUE}5️⃣  Checking Prometheus scraping...${NC}"
if kubectl get pods -n monitoring -l app=prometheus &>/dev/null; then
  PROMETHEUS_POD=$(kubectl get pods -n monitoring -l app=prometheus -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

  if [ -n "$PROMETHEUS_POD" ]; then
    for metric in "${METRICS[@]}"; do
      result=$(kubectl exec -n monitoring "$PROMETHEUS_POD" -- \
        wget -q -O- --timeout=5 "http://localhost:9090/api/v1/query?query=${metric}" 2>/dev/null | \
        jq -r '.data.result | length' 2>/dev/null || echo "0")

      if [ "$result" -gt 0 ]; then
        echo -e "   ${GREEN}✅ ${metric}${NC} (found $result series)"
      else
        echo -e "   ${YELLOW}⚠️  ${metric}${NC} (no data in Prometheus yet - may need time to scrape)"
      fi
    done
  else
    echo -e "   ${YELLOW}⚠️  Prometheus pod not found - skipping Prometheus checks${NC}"
  fi
else
  echo -e "   ${YELLOW}⚠️  Prometheus not available - skipping Prometheus checks${NC}"
fi
echo ""

# 6. Test metric updates (optional - checks if metrics are live)
echo -e "${BLUE}6️⃣  Testing metric updates...${NC}"
echo -e "   ${BLUE}ℹ️  Checking if metrics increment over time...${NC}"

# Get initial total count
INITIAL_COUNT=$(grep "^ta_bot_strategies_run_total" /tmp/ta-bot-metrics.txt 2>/dev/null | awk '{sum+=$2} END {print sum+0}')
echo -e "   ${BLUE}📊 Initial strategies_run_total: ${INITIAL_COUNT}${NC}"

# Wait 10 seconds
echo -e "   ${BLUE}⏳ Waiting 10 seconds...${NC}"
sleep 10

# Check updated value
kubectl exec -n petrosa-apps "$TA_BOT_POD" -- curl -s --max-time 5 http://localhost:8080/metrics > /tmp/ta-bot-metrics-updated.txt 2>/dev/null
UPDATED_COUNT=$(grep "^ta_bot_strategies_run_total" /tmp/ta-bot-metrics-updated.txt 2>/dev/null | awk '{sum+=$2} END {print sum+0}')
echo -e "   ${BLUE}📊 Updated strategies_run_total: ${UPDATED_COUNT}${NC}"

if [ "$UPDATED_COUNT" -gt "$INITIAL_COUNT" ]; then
  DIFF=$((UPDATED_COUNT - INITIAL_COUNT))
  echo -e "   ${GREEN}✅ Metrics are updating${NC} (+$DIFF in 10 seconds)"
else
  echo -e "   ${YELLOW}⚠️  Metrics did not update${NC} (may need to wait for next analysis cycle)"
  echo -e "   ${BLUE}ℹ️  Check pod logs: kubectl logs -n petrosa-apps $TA_BOT_POD${NC}"
fi
echo ""

# 7. Summary
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📋 Verification Summary${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ "$VERIFICATION_PASSED" = true ] && [ ${#FAILED_CHECKS[@]} -eq 0 ]; then
  echo -e "${GREEN}✅ ALL CHECKS PASSED${NC}"
  echo ""
  echo -e "${BLUE}Next steps:${NC}"
  echo "  1. Import Grafana dashboard from dashboards/ta-bot-business-metrics.json"
  echo "  2. Document baseline values in docs/METRICS_BASELINE.md"
  echo "  3. Capture dashboard screenshots"
  echo "  4. Update docs/RUNBOOK.md with verification section"
  exit 0
else
  echo -e "${RED}❌ VERIFICATION FAILED${NC}"
  echo ""
  echo -e "${YELLOW}Failed checks:${NC}"
  for check in "${FAILED_CHECKS[@]}"; do
    echo "  - $check"
  done
  echo ""
  echo -e "${BLUE}Troubleshooting:${NC}"
  echo "  1. Check TA Bot logs: kubectl logs -n petrosa-apps $TA_BOT_POD"
  echo "  2. Verify TA Bot configuration"
  echo "  3. Check if metrics endpoint is exposed on correct port"
  echo "  4. Review docs/METRICS_VERIFICATION.md for detailed troubleshooting"
  exit 1
fi
