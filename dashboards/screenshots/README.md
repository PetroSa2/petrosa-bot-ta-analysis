# TA Bot Business Metrics Dashboard Screenshots

**Purpose**: Visual documentation of the TA Bot business metrics dashboard for reference and onboarding.

**Related**: Issue #108, PR #106 (metrics implementation)

---

## Screenshot Guidelines

When capturing screenshots of the Grafana dashboard:

1. **Time Range**: Use "Last 24 hours" to show recent activity
2. **Resolution**: Minimum 1920x1080 for clarity
3. **Format**: PNG format preferred
4. **Naming**: Use descriptive names like:
   - `dashboard-overview.png` - Full dashboard view
   - `signal-generation-panel.png` - Signal generation metrics
   - `processing-latency-panel.png` - Latency histogram
   - `strategy-executions-panel.png` - Strategy execution metrics

## Required Screenshots

- [ ] Full dashboard overview (all 8 panels visible)
- [ ] Signal generation counter panel
- [ ] Signal processing duration histogram
- [ ] Strategies run counter panel
- [ ] Strategy executions (success/error) panel
- [ ] Configuration changes counter panel
- [ ] Any additional panels showing key insights

## Upload Instructions

1. Import dashboard into Grafana (see `docs/METRICS_VERIFICATION.md`)
2. Navigate to dashboard and set appropriate time range
3. Capture screenshots using browser screenshot tool or `Cmd+Shift+4` (macOS)
4. Save screenshots to this directory with descriptive names
5. Update this README to list captured screenshots

## Dashboard Location

**Grafana Dashboard**: `dashboards/ta-bot-business-metrics.json`

**Import Command**:
```bash
# Via Grafana UI:
# Dashboards → Import → Upload JSON file → Select dashboards/ta-bot-business-metrics.json

# Or via API:
curl -X POST "${GRAFANA_URL}/api/dashboards/db" \
  -H "Authorization: Bearer ${GRAFANA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d @dashboards/ta-bot-business-metrics.json
```

---

**Note**: Screenshots should be captured after baseline metrics are documented to show actual production data.
