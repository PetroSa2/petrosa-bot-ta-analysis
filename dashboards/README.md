# TA Bot Grafana Dashboards

This directory contains Grafana dashboard definitions for monitoring the TA Bot's business metrics.

## Available Dashboards

### ta-bot-business-metrics.json

Comprehensive business metrics dashboard for the TA Bot, including:

- **Total Signals (24h)**: Gauge showing total signals generated in the last 24 hours
- **Signal Generation Rate by Strategy**: Time series of signal generation rate per strategy
- **Signal Processing Latency**: Histogram showing p50, p95, and p99 latency
- **Active Strategies Count**: Number of strategies currently active
- **Strategy Execution Rate**: Success vs error rate for strategy executions
- **Configuration Changes**: Frequency of configuration updates
- **Top 10 Strategies**: Pie chart of most productive strategies
- **Signal Distribution**: BUY vs SELL signal breakdown

## Importing the Dashboard

### Option 1: Grafana UI

1. Log in to your Grafana instance
2. Click **Dashboards** → **Import** in the left sidebar
3. Click **Upload JSON file**
4. Select `ta-bot-business-metrics.json`
5. Select your Prometheus data source
6. Click **Import**

### Option 2: Grafana API

```bash
# Set your Grafana URL and API key
GRAFANA_URL="https://your-grafana-instance.com"
GRAFANA_API_KEY="your-api-key"

# Import the dashboard
curl -X POST "${GRAFANA_URL}/api/dashboards/db" \
  -H "Authorization: Bearer ${GRAFANA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d @ta-bot-business-metrics.json
```

### Option 3: Grafana Cloud

```bash
# Set your Grafana Cloud credentials
GRAFANA_CLOUD_URL="https://yourinstance.grafana.net"
GRAFANA_CLOUD_API_KEY="your-api-key"

# Import the dashboard
curl -X POST "${GRAFANA_CLOUD_URL}/api/dashboards/db" \
  -H "Authorization: Bearer ${GRAFANA_CLOUD_API_KEY}" \
  -H "Content-Type: application/json" \
  -d @ta-bot-business-metrics.json
```

## Metrics Reference

The dashboard uses the following OpenTelemetry metrics:

### Signal Generation Metrics

- **`ta_bot_signals_generated_total`**: Counter tracking signals generated
  - Labels: `symbol`, `timeframe`, `strategy`, `action`

- **`ta_bot_signal_processing_duration`**: Histogram of signal processing latency (ms)
  - Labels: `symbol`, `timeframe`, `signal_count`

### Strategy Metrics

- **`ta_bot_strategies_active`**: Gauge of active strategies count
  - Labels: `symbol`, `timeframe`

- **`ta_bot_strategy_executions_total`**: Counter of strategy executions
  - Labels: `strategy`, `symbol`, `timeframe`, `status`, `signal_generated`

### Configuration Metrics

- **`ta_bot_config_changes_total`**: Counter of configuration changes
  - Labels: `strategy_id`, `action`, `scope`, `symbol`, `changed_by`

## Prerequisites

- OpenTelemetry collector configured to export metrics to Prometheus
- Prometheus data source configured in Grafana
- TA Bot running with `OTEL_ENABLED=true`

## Customization

The dashboard uses a template variable `DS_PROMETHEUS` for the Prometheus data source. You can customize:

1. **Refresh interval**: Default is 10s (change in dashboard settings)
2. **Time range**: Default is last 6 hours (use time picker)
3. **Queries**: Edit panels to adjust PromQL queries
4. **Thresholds**: Add alert thresholds to panels

## Troubleshooting

### No data showing

1. Verify OpenTelemetry is enabled: Check TA Bot logs for "OpenTelemetry initialized"
2. Check metrics are being exported: Query Prometheus directly for `ta_bot_*` metrics
3. Verify data source: Ensure Prometheus data source is correctly configured

### Metrics missing

1. Ensure TA Bot has generated signals (metrics only appear after activity)
2. Check metric names: They should follow the pattern `ta_bot_*`
3. Verify label selectors: Ensure your queries match the actual labels

### Dashboard not importing

1. Check JSON syntax: Validate with a JSON linter
2. Ensure Grafana version compatibility: Dashboard created for Grafana 10+
3. Check permissions: Ensure you have dashboard creation permissions

## Support

For issues or questions:
- Check TA Bot logs: `kubectl logs -n petrosa-apps deployment/ta-bot`
- Verify metrics in Prometheus: Query `ta_bot_signals_generated_total`
- Review OpenTelemetry configuration: See `otel_init.py`
