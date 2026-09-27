# Petrosa TA Bot

The TA bot consumes candle data from the data-manager `/data/candles` API and
publishes technical-analysis signals. Configuration changes also go through
data-manager. The ta-bot holds no database connection and does not contain
database drivers.

## Runtime configuration

Set `DATA_MANAGER_URL`, `CONFIG_RATE_LIMIT_PER_AGENT`, and
`CONFIG_RATE_LIMIT_COOLDOWN`. Configuration mutations are rate limited through
data-manager and return HTTP 429 when the configured budget is exhausted.

## Storage boundary

MongoDB is the operational store owned by data-manager. Historical MySQL data
is accessed only by data-manager for research and backtesting; ta-bot never
connects to either database directly.

## Development

```bash
make pipeline
```

The pipeline runs Ruff, mypy, and the pytest coverage suite.
