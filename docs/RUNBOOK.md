# TA Bot Operations Runbook

This runbook provides step-by-step procedures for common operational tasks and troubleshooting scenarios.

## Table of Contents

- [Metrics Verification](#metrics-verification)
- [Signal Generation Issues](#signal-generation-issues)
- [Performance Issues](#performance-issues)
- [Configuration Management](#configuration-management)
- [Database Connection Issues](#database-connection-issues)
- [NATS Connection Issues](#nats-connection-issues)

---

## Metrics Verification

### Quick Verification

**Automated Script** (Recommended):
```bash
# Run comprehensive verification script
./scripts/verify-metrics.sh

# Expected output:
# ✅ ALL CHECKS PASSED
```

For detailed verification procedures, troubleshooting, and baseline documentation, see:
- **[METRICS_VERIFICATION.md](./METRICS_VERIFICATION.md)** - Complete verification guide
- **[METRICS_BASELINE.md](./METRICS_BASELINE.md)** - Baseline metrics template
- **[verify-metrics.sh](../scripts/verify-metrics.sh)** - Automated verification script

### Prerequisites and Deployment Status

**Required Version**: v1.0.68+ (contains metrics from PR #106)

**Check Current Deployment Version**:
```bash
kubectl --kubeconfig=k8s/kubeconfig.yaml get deployment petrosa-ta-bot -n petrosa-apps \
  -o jsonpath='{.spec.template.spec.containers[0].image}'

# Example output: yurisa2/petrosa-ta-bot:v1.0.68
```

**If version < v1.0.68**:
- Metrics code is merged but not yet deployed
- Wait for CI/CD to build and deploy new image (5-15 minutes)
- Monitor deployment: `gh run list --repo PetroSa2/petrosa-bot-ta-analysis`
- Watch rollout: `kubectl rollout status deployment/petrosa-ta-bot -n petrosa-apps -w`

**Prerequisites**:
- TA Bot deployed with version containing metrics (v1.0.68+)
- OpenTelemetry enabled (`OTEL_ENABLED=true`)
- Access to Kubernetes cluster

**Step 1: Check Pod Status**

```bash
kubectl --kubeconfig=k8s/kubeconfig.yaml get pods -n petrosa-apps -l app=petrosa-ta-bot

# Expected: 3 pods in Running state
```

**Step 2: Check Logs for OpenTelemetry Initialization**

```bash
kubectl --kubeconfig=k8s/kubeconfig.yaml logs -n petrosa-apps deployment/petrosa-ta-bot --tail=50 | grep -i "otel\|telemetry"

# Expected output:
# - "OpenTelemetry SDK initialized"
# - "Meter provider configured"
# - "Exporter endpoint: https://otlp-gateway-prod-us-central-0.grafana.net/otlp"
```

**Step 3: Verify Metrics Endpoint**

```bash
# Port-forward to TA Bot pod
kubectl --kubeconfig=k8s/kubeconfig.yaml port-forward -n petrosa-apps deployment/petrosa-ta-bot 8080:8080 &
PF_PID=$!

# Wait for port-forward
sleep 3

# Check metrics endpoint
curl -s http://localhost:8080/metrics | grep "ta_bot_" | head -20

# Stop port-forward
kill $PF_PID

# Expected metrics:
# - ta_bot_signals_generated_total
# - ta_bot_signal_processing_duration
# - ta_bot_strategies_run_total
# - ta_bot_strategy_executions_total
# - ta_bot_config_changes_total
```

**Step 4: Query Metrics from Prometheus**

If Prometheus is deployed in the cluster:

```bash
# Check if Prometheus deployment exists
kubectl --kubeconfig=k8s/kubeconfig.yaml get deployments -n monitoring

# Port-forward to Prometheus (if available)
kubectl --kubeconfig=k8s/kubeconfig.yaml port-forward -n monitoring svc/prometheus 9090:9090 &
PROM_PID=$!
sleep 3

# Query for TA Bot metrics
curl -s "http://localhost:9090/api/v1/label/__name__/values" | jq -r '.data[]' | grep "ta_bot_"

# Query specific metric
curl -s "http://localhost:9090/api/v1/query?query=ta_bot_signals_generated_total" | jq .

# Stop port-forward
kill $PROM_PID
```

**Step 5: Test Metric Recording**

```bash
# Trigger signal generation
curl -X POST http://localhost:8080/api/v1/test/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTCUSDT","timeframe":"1h"}'

# Wait for processing
sleep 10

# Check if counter incremented
curl -s "http://localhost:9090/api/v1/query?query=ta_bot_signals_generated_total" | jq '.data.result[].value'
```

**Troubleshooting**:

| Issue | Cause | Solution |
|-------|-------|----------|
| No metrics endpoint | Old version deployed | Check image tag, wait for CI/CD deployment |
| Metrics endpoint returns empty | OTel not initialized | Check `OTEL_ENABLED=true` in deployment |
| Metrics not in Prometheus | Scraping not configured | Add ServiceMonitor or Prometheus scrape config |
| Old metric values | Cache issue | Restart Prometheus or wait for scrape interval |

---

## Signal Generation Issues

### No Signals Being Generated

**Symptom**: Alert `TABotNoSignalsGenerated` firing, or manual check shows zero signals.

**Diagnostic Steps**:

```bash
# 1. Check TA Bot is running
kubectl --kubeconfig=k8s/kubeconfig.yaml get pods -n petrosa-apps -l app=petrosa-ta-bot

# 2. Check logs for errors
kubectl --kubeconfig=k8s/kubeconfig.yaml logs -n petrosa-apps deployment/petrosa-ta-bot --tail=200 | grep -i "error\|exception\|fail"

# 3. Check leader election status
kubectl --kubeconfig=k8s/kubeconfig.yaml exec -n petrosa-apps deployment/petrosa-ta-bot -- curl -s http://localhost:8080/health | jq '.leader_election'

# Expected: One pod should be leader=true

# 4. Check database connectivity
kubectl --kubeconfig=k8s/kubeconfig.yaml exec -n petrosa-apps deployment/petrosa-ta-bot -- curl -s http://localhost:8080/health | jq '.mysql'

# Expected: status="connected"

# 5. Manually trigger analysis
kubectl --kubeconfig=k8s/kubeconfig.yaml exec -n petrosa-apps deployment/petrosa-ta-bot -- \
  curl -X POST http://localhost:8080/api/v1/test/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTCUSDT","timeframe":"1h"}'
```

**Common Causes**:
- Leader election stuck (no active leader)
- MySQL connection failed
- Insufficient candle data in database
- All strategies disabled in configuration

**Resolution**:
- Restart deployment if leader election stuck
- Verify MySQL credentials in secret
- Check Data Extractor is running and populating data
- Review strategy configuration

---

## Performance Issues

### High Processing Latency

**Symptom**: Alert `TABotHighLatency` firing, or p99 latency >5000ms.

**Diagnostic Steps**:

```bash
# 1. Check current latency
curl -s "http://prometheus:9090/api/v1/query?query=histogram_quantile(0.99, rate(ta_bot_signal_processing_duration_bucket[5m]))" | jq '.data.result[].value'

# 2. Check by symbol/timeframe
curl -s "http://prometheus:9090/api/v1/query?query=histogram_quantile(0.99, rate(ta_bot_signal_processing_duration_bucket{symbol='BTCUSDT'}[5m]))" | jq .

# 3. Check resource usage
kubectl --kubeconfig=k8s/kubeconfig.yaml top pods -n petrosa-apps -l app=petrosa-ta-bot

# 4. Check database query performance
kubectl --kubeconfig=k8s/kubeconfig.yaml logs -n petrosa-apps deployment/petrosa-ta-bot | grep "Fetched.*candles" | tail -10
```

**Common Causes**:
- Large candle datasets (>1000 rows)
- CPU throttling
- Slow MySQL queries
- Too many strategies enabled

**Resolution**:
- Reduce candle lookback period
- Increase CPU limits
- Add MySQL indexes
- Disable underperforming strategies

---

## Configuration Management

> **Note**: The service URLs used below (e.g., `petrosa-ta-bot-service:80`) are only accessible from within the Kubernetes cluster.
>
> To run these commands from outside the cluster, use one of these approaches:
>
> **Option 1: Port-forward to service**
> ```bash
> kubectl --kubeconfig=k8s/kubeconfig.yaml port-forward -n petrosa-apps svc/petrosa-ta-bot-service 8080:80 &
> curl http://localhost:8080/api/v1/strategies/rsi/config | jq .
> # Kill port-forward when done: kill %1
> ```
>
> **Option 2: Execute from within a pod**
> ```bash
> kubectl --kubeconfig=k8s/kubeconfig.yaml exec -n petrosa-apps deployment/petrosa-ta-bot -- \
>   curl http://petrosa-ta-bot-service:80/api/v1/strategies/rsi/config
> ```

### Testing Configuration Changes

```bash
# Get current configuration
curl http://petrosa-ta-bot-service:80/api/v1/strategies/rsi/config | jq .

# Update global configuration
curl -X PUT http://petrosa-ta-bot-service:80/api/v1/strategies/rsi/config \
  -H "Content-Type: application/json" \
  -d '{
    "period": 14,
    "overbought": 70,
    "oversold": 30
  }'

# Verify config change metric incremented
curl -s "http://prometheus:9090/api/v1/query?query=ta_bot_config_changes_total{action='update'}" | jq .

# Set symbol-specific override
curl -X PUT http://petrosa-ta-bot-service:80/api/v1/strategies/rsi/config/BTCUSDT \
  -H "Content-Type: application/json" \
  -d '{
    "period": 10,
    "overbought": 75
  }'

# Delete symbol override (revert to global)
curl -X DELETE http://petrosa-ta-bot-service:80/api/v1/strategies/rsi/config/BTCUSDT

# Force cache refresh
curl -X POST http://petrosa-ta-bot-service:80/api/v1/strategies/cache/refresh
```

---

## Database Connection Issues

### MySQL Connection Failed

**Symptom**: Logs show "Cannot connect to MySQL" or health check shows mysql status=disconnected.

```bash
# 1. Verify MySQL service exists
kubectl --kubeconfig=k8s/kubeconfig.yaml get svc -n petrosa-apps | grep mysql

# 2. Test MySQL connectivity from TA Bot pod
kubectl --kubeconfig=k8s/kubeconfig.yaml exec -n petrosa-apps deployment/petrosa-ta-bot -- nc -zv mysql 3306

# 3. Check MySQL credentials in secret
kubectl --kubeconfig=k8s/kubeconfig.yaml get secret petrosa-sensitive-credentials -n petrosa-apps -o jsonpath='{.data.mysql-uri}' | base64 --decode

# 4. Check MySQL pod logs
kubectl --kubeconfig=k8s/kubeconfig.yaml logs -n petrosa-apps deployment/mysql --tail=50
```

**Resolution**:
- Verify MySQL secret is correct
- Restart MySQL if crashed
- Check network policy allows TA Bot → MySQL

---

## NATS Connection Issues

### NATS Publisher Not Connected

**Symptom**: Signals generated but not published, health check shows nats status=disconnected.

```bash
# 1. Check NATS server
kubectl --kubeconfig=k8s/kubeconfig.yaml get pods -n nats

# 2. Test NATS connectivity
kubectl --kubeconfig=k8s/kubeconfig.yaml exec -n petrosa-apps deployment/petrosa-ta-bot -- nc -zv nats-server.nats 4222

# 3. Check NATS logs
kubectl --kubeconfig=k8s/kubeconfig.yaml logs -n nats deployment/nats-server --tail=50

# 4. Restart TA Bot to force reconnection
kubectl --kubeconfig=k8s/kubeconfig.yaml rollout restart deployment/petrosa-ta-bot -n petrosa-apps
```

**Resolution**:
- Verify NATS_URL in configuration
- Check network policy allows TA Bot → NATS
- Restart NATS if crashed

---

## Emergency Procedures

### Rollback to Previous Version

```bash
# Check rollout history
kubectl --kubeconfig=k8s/kubeconfig.yaml rollout history deployment/petrosa-ta-bot -n petrosa-apps

# Rollback to previous version
kubectl --kubeconfig=k8s/kubeconfig.yaml rollout undo deployment/petrosa-ta-bot -n petrosa-apps

# Rollback to specific revision
kubectl --kubeconfig=k8s/kubeconfig.yaml rollout undo deployment/petrosa-ta-bot -n petrosa-apps --to-revision=5
```

### Scale Down (Emergency)

```bash
# Scale to 1 replica
kubectl --kubeconfig=k8s/kubeconfig.yaml scale deployment/petrosa-ta-bot --replicas=1 -n petrosa-apps

# Scale to 0 (complete shutdown)
kubectl --kubeconfig=k8s/kubeconfig.yaml scale deployment/petrosa-ta-bot --replicas=0 -n petrosa-apps

# Restore to 3 replicas
kubectl --kubeconfig=k8s/kubeconfig.yaml scale deployment/petrosa-ta-bot --replicas=3 -n petrosa-apps
```

---

## Health Check Reference

### Health Endpoints

> **Note**: These URLs work from within the cluster. For external access, use `kubectl port-forward` or `kubectl exec` as shown in the Configuration Management section above.

```bash
# Liveness probe
curl http://petrosa-ta-bot-service:80/healthz

# Readiness probe
curl http://petrosa-ta-bot-service:80/ready

# Detailed health
curl http://petrosa-ta-bot-service:80/health | jq .

# Metrics
curl http://petrosa-ta-bot-service:80/metrics
```

### Expected Health Response

```json
{
  "status": "healthy",
  "service": "ta-bot",
  "version": "1.0.68",
  "uptime_seconds": 3600,
  "leader_election": {
    "enabled": true,
    "is_leader": true,
    "leader_id": "petrosa-ta-bot-7c998b6bf4-spgqs"
  },
  "mysql": {
    "status": "connected",
    "latency_ms": 12.5
  },
  "mongodb": {
    "status": "connected",
    "latency_ms": 45.2
  },
  "nats": {
    "status": "connected",
    "published_signals": 1234
  }
}
```

---

## Contact and Escalation

For issues not covered in this runbook:
- Check service logs for detailed error messages
- Review GitHub issues for known problems
- Contact development team via GitHub issues
