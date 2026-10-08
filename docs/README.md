# Petrosa TA Bot Documentation

This directory contains the current operational and design documentation for
the technical-analysis bot.

## Start here

- [Documentation index](INDEX.md) — current documents and their purpose.
- [Runbook](RUNBOOK.md) — storage boundaries, troubleshooting, and verification.
- [Backtest](BACKTEST.md) — backtest workflow and artifact contract.
- [Security](SECURITY.md) — service security boundaries and controls.

The service consumes candles and configuration through data-manager APIs,
publishes technical-analysis signals, and does not connect to databases
directly. Use the repository [README](../README.md) and `AGENTS.md` for
development commands and contribution rules.
