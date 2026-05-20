"""Module entrypoint: `python -m backtest --strategy … --from … --to …`."""

from __future__ import annotations

from backtest.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
