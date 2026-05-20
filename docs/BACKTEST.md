# Backtest engine (MVP, P3.1)

Replays one registered TA strategy against historical candles fetched from
`petrosa-data-manager` and emits a *characterization artifact* that the P3.2
evaluator can consume. Tracks `decision_id` per the
[cross-service identifier contract](https://github.com/PetroSa2/petrosa_k8s/blob/main/docs/cross-service-identifier-contract.md).

This is the MVP scope of
[#233](https://github.com/PetroSa2/petrosa-bot-ta-analysis/issues/233). The
persistence and reproducibility infrastructure (P3.2) is intentionally
not yet wired in — the artifact is emitted to a file or stdout for the
evaluator to pick up directly.

## CLI

```bash
python -m backtest \
  --strategy ema_alignment_bullish \
  --from 2026-01-01 \
  --to 2026-12-31 \
  --symbol BTCUSDT \
  --period 15m \
  --output /tmp/backtest.json
```

Flags:

| flag | required | default | meaning |
| --- | --- | --- | --- |
| `--strategy` | yes | — | Registered strategy_id (see `ta_bot/core/signal_engine.py`) |
| `--from` | yes | — | ISO-8601 start of the date window (UTC if no tz) |
| `--to` | yes | — | ISO-8601 end of the date window (UTC if no tz) |
| `--symbol` | no | `BTCUSDT` | Trading symbol |
| `--period` | no | `15m` | Candle period |
| `--warmup` | no | `200` | Candles required before strategies evaluate |
| `--fixture` | no | — | JSON fixture path (offline mode — bypasses data-manager) |
| `--max-candles` | no | `1000` | Cap on data-manager fetches (live mode only) |
| `--output` | no | stdout | Where to write the artifact JSON |
| `--log-level` | no | `INFO` | `DEBUG\|INFO\|WARNING\|ERROR` |

## Artifact schema (v1.0.0)

```json
{
  "schema_version": "1.0.0",
  "strategy_id": "ema_alignment_bullish",
  "symbol": "BTCUSDT",
  "period": "15m",
  "range_from": "2026-01-01T00:00:00+00:00",
  "range_to":   "2026-12-31T00:00:00+00:00",
  "candle_count": 260,
  "signal_count": 95,
  "source": "backtest",
  "events": [
    {
      "decision_id": "dec_20260102T070000000_16d90f",
      "candle_timestamp": "2026-01-02T07:00:00+00:00",
      "action": "buy",
      "confidence": 0.89,
      "current_price": 50123.45,
      "metadata": {"strength": "medium", "strategy_mode": "deterministic"}
    }
  ]
}
```

`decision_id` follows the production contract shape `dec_{compact_ts}_{6hex}`.
The hex suffix is derived deterministically from
`(strategy_id, symbol, candle_timestamp, sequence)` so a re-run against the
same window yields a byte-identical artifact — the reproducibility AC.

## Reproducibility

The engine guarantees that two runs with the same `(strategy_id, symbol,
period, range_from, range_to, warmup, fixture_or_data_source)` produce
byte-identical artifact JSON. There is no wall-clock time, no RNG, and no
network ordering involved on the engine path; the upstream data source
must itself be deterministic for the guarantee to hold (the offline
fixture trivially is).

## Tests

```bash
venv/bin/python -m pytest tests/backtest/
```

The end-to-end test (`tests/backtest/test_engine_e2e.py`) runs
`ema_alignment_bullish` against a recorded JSON fixture
(`tests/backtest/fixtures/candles_BTCUSDT_15m_recorded.json`) and asserts
non-zero signal emission plus reproducibility.

## Out of scope (handled later)

- Persistence of the artifact in `petrosa-data-manager` (P3.2).
- Position sizing, P&L computation, win/loss stats (P3.2 / P2.3).
- Multi-strategy comparison runs (P2.3 strategy-fidelity evaluator).
- Live → backtest signal-fidelity comparison (P2.3).
