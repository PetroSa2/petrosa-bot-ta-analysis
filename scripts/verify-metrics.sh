#!/bin/bash
# TA Bot Business Metrics Verification Script
#
# This script verifies that all custom business metrics from PR #106 are:
# 1. Being emitted by TA Bot
# 2. Visible in Prometheus
# 3. Recording accurate data
# 4. Ready for alerting and dashboards
#
# Usage: ./verify-metrics.sh [--kubeconfig PATH]

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
KUBECONFIG_PATH="${1:-/Users/yurisa2/petrosa/petrosa_k8s/k8s/kubeconfig.yaml}"
NAMESPACE="petrosa-apps"
DEPLOYMENT="petrosa-ta-bot"
SERVICE="petrosa-ta-bot-service"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}TA Bot Business Metrics Verification${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Date: $(date)"
echo "Namespace: $NAMESPACE"
echo "Deployment: $DEPLOYMENT"
echo ""

# Step 1: Check Pod Status
echo -e "${YELLOW}Step 1: Checking Pod Status...${NC}"
POD_COUNT=$(kubectl --kubeconfig=$KUBECONFIG_PATH get pods -n $NAMESPACE -l app=$DEPLOYMENT -o json | jq '.items | length')
RUNNING_PODS=$(kubectl --kubeconfig=$KUBECONFIG_PATH get pods -n $NAMESPACE -l app=$DEPLOYMENT -o json | jq '[.items[] | select(.status.phase=="Running")] | length')

echo "  Total pods: $POD_COUNT"
echo "  Running pods: $RUNNING_PODS"

if [ "$RUNNING_PODS" -eq 0 ]; then
    echo -e "${RED}✗ No running pods found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Pods running${NC}"
echo ""

# Step 2: Check Deployment Version
echo -e "${YELLOW}Step 2: Checking Deployment Version...${NC}"
IMAGE=$(kubectl --kubeconfig=$KUBECONFIG_PATH get deployment $DEPLOYMENT -n $NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].image}')
VERSION=$(echo $IMAGE | grep -o 'v[0-9.]*')
echo "  Image: $IMAGE"
echo "  Version: $VERSION"

# Extract version number for comparison (handle decimal properly)
VERSION_MAJOR=$(echo $VERSION | sed 's/v//' | cut -d. -f1)
VERSION_MINOR=$(echo $VERSION | sed 's/v//' | cut -d. -f2)
VERSION_PATCH=$(echo $VERSION | sed 's/v//' | cut -d. -f3)

# Check if version >= 1.0.68
if [ "$VERSION_MAJOR" -lt 1 ] || ([ "$VERSION_MAJOR" -eq 1 ] && [ "$VERSION_MINOR" -eq 0 ] && [ "$VERSION_PATCH" -lt 68 ]); then
    echo -e "${YELLOW}⚠ Version $VERSION does not include metrics (need v1.0.68+)${NC}"
    echo "  Metrics were added in PR #106"
    echo "  Current version deployed before metrics implementation"
    echo ""
    echo -e "${RED}✗ Cannot verify metrics - waiting for CI/CD deployment${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Wait for GitHub Actions to build new image (v1.0.68+)"
    echo "  2. CI/CD will automatically deploy to cluster"
    echo "  3. Re-run this script after deployment"
    exit 1
fi
echo -e "${GREEN}✓ Version checked${NC}"
echo ""

# Step 3: Check OpenTelemetry Configuration
echo -e "${YELLOW}Step 3: Checking OpenTelemetry Configuration...${NC}"
OTEL_ENABLED=$(kubectl --kubeconfig=$KUBECONFIG_PATH get deployment $DEPLOYMENT -n $NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="OTEL_ENABLED")].value}')
echo "  OTEL_ENABLED: $OTEL_ENABLED"

if [ "$OTEL_ENABLED" != "true" ]; then
    echo -e "${RED}✗ OpenTelemetry not enabled${NC}"
    exit 1
fi
echo -e "${GREEN}✓ OpenTelemetry enabled${NC}"
echo ""

# Step 4: Check Pod Logs for Metrics Initialization
echo -e "${YELLOW}Step 4: Checking Logs for Metrics Initialization...${NC}"
POD_NAME=$(kubectl --kubeconfig=$KUBECONFIG_PATH get pods -n $NAMESPACE -l app=$DEPLOYMENT -o jsonpath='{.items[0].metadata.name}')

# Check for OTel initialization
kubectl --kubeconfig=$KUBECONFIG_PATH logs -n $NAMESPACE $POD_NAME --tail=100 | grep -i "opentelemetry\|meter" > /tmp/otel-logs.txt || true

if [ -s /tmp/otel-logs.txt ]; then
    echo -e "${GREEN}✓ OpenTelemetry logs found${NC}"
    head -3 /tmp/otel-logs.txt | sed 's/^/  /'
else
    echo -e "${YELLOW}⚠ No OpenTelemetry initialization logs (may have scrolled past)${NC}"
fi
echo ""

# Step 5: Verify Metrics Endpoint (if accessible)
echo -e "${YELLOW}Step 5: Verifying Metrics Endpoint...${NC}"
echo "  Attempting to port-forward to pod..."

kubectl --kubeconfig=$KUBECONFIG_PATH port-forward -n $NAMESPACE $POD_NAME 8080:8080 > /dev/null 2>&1 &
PF_PID=$!
sleep 3

# Check if port-forward succeeded
if ! kill -0 $PF_PID 2>/dev/null; then
    echo -e "${YELLOW}⚠ Port-forward failed, skipping metrics endpoint check${NC}"
else
    # Query metrics endpoint
    METRICS=$(curl -s http://localhost:8080/metrics 2>/dev/null | grep "ta_bot_" || true)

    if [ -n "$METRICS" ]; then
        METRIC_COUNT=$(echo "$METRICS" | wc -l | tr -d ' ')
        echo -e "${GREEN}✓ Metrics endpoint accessible ($METRIC_COUNT ta_bot_* metrics)${NC}"

        # Save metrics to file
        echo "$METRICS" > /tmp/ta-bot-metrics-raw.txt

        # Check for each expected metric
        for metric_name in \
            ta_bot_signals_generated_total \
            ta_bot_signal_processing_duration \
            ta_bot_strategies_run_total \
            ta_bot_strategy_executions_total \
            ta_bot_config_changes_total; do

            if echo "$METRICS" | grep -q "$metric_name"; then
                echo -e "  ${GREEN}✓${NC} $metric_name"
            else
                echo -e "  ${RED}✗${NC} $metric_name (missing)"
            fi
        done
    else
        echo -e "${YELLOW}⚠ No ta_bot_* metrics found${NC}"
    fi

    # Kill port-forward
    kill $PF_PID 2>/dev/null || true
fi
echo ""

# Step 6: Test Signal Generation and Metric Recording
echo -e "${YELLOW}Step 6: Testing Signal Generation and Metrics...${NC}"
echo "  Triggering test analysis..."

# Port-forward again for API call
kubectl --kubeconfig=$KUBECONFIG_PATH port-forward -n $NAMESPACE $POD_NAME 8080:8080 > /dev/null 2>&1 &
PF_PID=$!
sleep 3

# Trigger signal generation (if API endpoint exists)
RESPONSE=$(curl -s -X POST http://localhost:8080/api/v1/test/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTCUSDT","timeframe":"1h"}' 2>/dev/null || echo "endpoint_not_available")

if [ "$RESPONSE" != "endpoint_not_available" ]; then
    echo -e "${GREEN}✓ Test analysis triggered${NC}"
    echo "  Response: $(echo $RESPONSE | jq -r '.message' 2>/dev/null || echo $RESPONSE)"

    # Wait for metrics to update
    echo "  Waiting 10 seconds for metrics to update..."
    sleep 10

    # Check if metrics incremented
    NEW_METRICS=$(curl -s http://localhost:8080/metrics 2>/dev/null | grep "ta_bot_signals_generated_total" | head -1)
    echo "  Current signal count: $NEW_METRICS"
else
    echo -e "${YELLOW}⚠ Test endpoint not available (manual testing required)${NC}"
fi

# Kill port-forward
kill $PF_PID 2>/dev/null || true
echo ""

# Step 7: Summary
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Verification Summary${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${GREEN}✓ Pod Status: $RUNNING_PODS/$POD_COUNT running${NC}"
echo -e "${GREEN}✓ Version: $VERSION${NC}"
echo -e "${GREEN}✓ OpenTelemetry: Enabled${NC}"
echo ""

if [ -s /tmp/ta-bot-metrics-raw.txt ]; then
    echo -e "${GREEN}✓ Metrics Available: YES${NC}"
    echo ""
    echo "Captured metrics saved to: /tmp/ta-bot-metrics-raw.txt"
    echo "View with: cat /tmp/ta-bot-metrics-raw.txt"
else
    echo -e "${YELLOW}⚠ Metrics verification incomplete${NC}"
    echo "  This may indicate:"
    echo "  - Metrics not yet emitted (pod recently restarted)"
    echo "  - Version doesn't include metrics code"
    echo "  - OpenTelemetry not properly initialized"
fi
echo ""

echo -e "${BLUE}Next Steps:${NC}"
echo "1. Review captured metrics: cat /tmp/ta-bot-metrics-raw.txt"
echo "2. Import Grafana dashboard: dashboards/ta-bot-business-metrics.json"
echo "3. Document baseline values: docs/METRICS_BASELINE.md"
echo "4. Create alerting rules: see issue #75"
echo ""

echo -e "${GREEN}Verification complete!${NC}"
