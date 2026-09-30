# Agent instructions: petrosa-bot-ta-analysis

The TA bot consumes candle data from the data-manager `/data/candles` API and publishes technical-analysis signals.

Ecosystem rules (data pillars, commit and PR process, wording, memory) are in the umbrella [AGENTS.md](https://github.com/PetroSa2/petrosa/blob/main/AGENTS.md); this file covers this repository only. Only statements that can be checked against the repository are listed as facts.

## Commands (from the Makefile)

| Command | Purpose |
|---|---|
| `make setup` | Complete environment setup |
| `make lint` | Run all linters (ruff) |
| `make format` | Format code with black and ruff |
| `make type-check` | Run static type checking with mypy |
| `make test` | Run unit tests |
| `make security` | Run security scans (gitleaks, bandit, trivy) |
| `make pipeline` | Run complete CI pipeline locally |
| `make test-quality` | Run test quality check (assertions check) |

Run the local pipeline or at least lint and tests before opening a pull request.

## Facts

- Python: `.python-version` is `3.11.9`.
- Lint and format: ruff (config in `ruff.toml`).
- Type checking: mypy (config in `mypy.ini`).
- Tests: pytest, in `tests/`; the coverage floor is 18%.
- `make test-quality` checks that tests contain assertions.
- Container image: built from `Dockerfile`.
- Instrumentation uses the internal `petrosa-otel` package.
- CI workflows: `.github/workflows/ci-checks.yml`, `.github/workflows/deploy.yml`, `.github/workflows/manual-deploy.yml`.

## Layout

Python packages at the top level: `backtest/`, `ta_bot/`. Also `tests/`, `docs/` and `scripts/` where they exist.

## Rules (policy)

- Do not add database drivers or connections to this service. Read and write data through the data-manager API.
- Candles come from the data-manager `/data/candles` API; configuration changes also go through data-manager.
- This service holds no database connection. Treat "Data-manager unreachable" as the storage connectivity failure.
- Commits use Conventional Commits; branches are `{type}/{issue-number}-{slug}`; a PR body contains `Closes #N`; never merge with `--admin`.
- Text that leaves the repository (PR titles and bodies, commit messages, code comments) uses generic roles such as Agentic Developer and never names the upstream workflow engine or its personas.
- Do not commit logs, drafts, scratch files or generated working notes. GitHub and the memory server are the record.
