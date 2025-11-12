# TA Bot Grafana Dashboard Screenshots

This directory contains screenshots of the TA Bot business metrics Grafana dashboard for documentation purposes.

## Purpose

- **Documentation**: Visual reference for dashboard layout and metrics
- **Baseline Recording**: Capture initial metric values after deployment
- **Troubleshooting**: Compare current dashboard with baseline
- **Onboarding**: Help new team members understand monitoring setup

## Required Screenshots

After dashboard is imported and verified (Issue #108), capture:

1. **`01-overview.png`** - Full dashboard view showing all 8 panels
2. **`02-signal-generation.png`** - Signal generation counter by strategy
3. **`03-processing-latency.png`** - Signal processing duration histogram
4. **`04-strategies-run.png`** - Strategies run counter by symbol
5. **`05-strategy-executions.png`** - Strategy execution success/error rates
6. **`06-config-changes.png`** - Configuration change counter over time
7. **`07-time-series.png`** - Time series graphs showing trends
8. **`08-current-values.png`** - Current metric values and gauges

## How to Capture

### Option 1: Grafana UI Screenshot

```bash
# 1. Access Grafana
GRAFANA_URL=$(kubectl get ingress grafana -n monitoring -o jsonpath='{.spec.rules[0].host}')
GRAFANA_PASS=$(kubectl get secret grafana-admin -n monitoring -o jsonpath='{.data.password}' | base64 --decode)

echo "Open: https://${GRAFANA_URL}"
echo "User: admin"
echo "Pass: ${GRAFANA_PASS}"

# 2. Navigate to TA Bot dashboard
# 3. Use browser screenshot tool or Grafana's built-in "Share" > "Image" export
```

### Option 2: Automated Screenshot (with Grafana API)

```bash
# Install grafana-image-renderer (if available)
# Then use Grafana API to render dashboard images

GRAFANA_API_KEY=$(kubectl get secret grafana-api-key -n monitoring -o jsonpath='{.data.key}' | base64 --decode)

curl "https://${GRAFANA_URL}/render/d-solo/ta-bot-business-metrics/ta-bot-business-metrics?orgId=1&panelId=1&width=1000&height=500&tz=UTC" \
  -H "Authorization: Bearer ${GRAFANA_API_KEY}" \
  -o 01-overview.png
```

### Option 3: Manual Screenshots

1. Login to Grafana
2. Navigate to **Dashboards** > **TA Bot Business Metrics**
3. Use OS screenshot tool:
   - **macOS**: Cmd+Shift+4
   - **Windows**: Win+Shift+S
   - **Linux**: Depends on distro (often PrtSc or Shift+PrtSc)
4. Save to this directory with appropriate naming

## Naming Convention

Use descriptive prefixes to indicate content:
- `01-`, `02-`, etc. for sequence
- Lowercase with hyphens
- `.png` format preferred (high quality)

## Update Schedule

Screenshots should be updated:
- ✅ **Initial**: After metrics verification (Issue #108)
- 🔄 **After Major Changes**: Dashboard layout changes, new metrics added
- 📅 **Quarterly**: To reflect evolving baseline values
- 🐛 **After Incidents**: To document before/after states

## Usage in Documentation

Reference screenshots in documentation:
```markdown
![TA Bot Dashboard Overview](./dashboards/screenshots/01-overview.png)
```

Or link directly:
```markdown
[View Dashboard Screenshot](./dashboards/screenshots/01-overview.png)
```

## Notes

- Screenshots show production data - review for sensitive information before committing
- Ensure dashboard is in a representative state (not during an incident)
- Include timestamp/date range visible in screenshot
- Crop or annotate as needed for clarity
