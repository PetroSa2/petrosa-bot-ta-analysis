# TA Bot runbook

## Storage and configuration

- Candles come from the data-manager `/data/candles` endpoint.
- Configuration is read and written through data-manager.
- ta-bot holds no database connection and requires no database URI.

## Troubleshooting

If the health evaluator reports **Data-manager unreachable**, check
`DATA_MANAGER_URL`, the data-manager liveness endpoint, and the service
network path. Do not add database credentials or a direct database client to
the bot.

## Rate limiting

Configuration mutations use the data-manager rate limiter. A 429 response is
the expected result when the per-agent limit or cooldown is active.

## Verification

Run `make pipeline` after code changes. Inspect application logs and the
data-manager health endpoint when startup or configuration calls fail.
