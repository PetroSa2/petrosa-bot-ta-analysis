from datetime import UTC, datetime

from ta_bot.backtest.correlation import daily_pnl_correlation
from ta_bot.backtest.stats import (
    block_bootstrap_expectancy_ci,
    independent_bootstrap_expectancy_ci,
)
from ta_bot.backtest.walkforward import walk_forward


def trade(day: int, pnl: str, symbol: str = "BTCUSDT") -> dict[str, str]:
    timestamp = datetime(2026, 1, day, tzinfo=UTC).isoformat()
    return {"exit_time": timestamp, "net_pnl": pnl, "symbol": symbol}


def test_bootstrap_is_seeded_and_reports_sample_status() -> None:
    trades = [trade(1, "1"), trade(1, "3"), trade(2, "-1")]
    first = block_bootstrap_expectancy_ci(trades, seed=4, n_boot=20, min_trades=4)
    assert first == block_bootstrap_expectancy_ci(
        trades, seed=4, n_boot=20, min_trades=4
    )
    assert first["sample_ok"] is False
    assert first != block_bootstrap_expectancy_ci(
        trades, seed=5, n_boot=20, min_trades=4
    )


def test_block_bootstrap_is_available_as_a_clustered_comparison() -> None:
    trades = [trade(1, "10"), trade(1, "10"), trade(2, "-10"), trade(2, "-10")]
    block = block_bootstrap_expectancy_ci(trades, seed=3, n_boot=100)
    independent = independent_bootstrap_expectancy_ci(trades, seed=3, n_boot=100)
    block_width = float(block["ci"][1]) - float(block["ci"][0])
    independent_width = float(independent["ci"][1]) - float(independent["ci"][0])
    assert block_width >= independent_width


def test_correlation_zero_pads_gaps() -> None:
    trades = [
        trade(1, "1", "A"),
        trade(1, "2", "B"),
        trade(3, "1", "A"),
        trade(3, "2", "B"),
    ]
    result = daily_pnl_correlation(trades)
    assert result["n_days"] == 3
    assert result["correlations"]["A|B"] == 1.0


def test_walk_forward_keeps_train_and_test_separate() -> None:
    trades = [trade(day, str(day)) for day in range(1, 7)]
    reports = walk_forward(trades, train_days=2, test_days=2, step_days=2)
    assert len(reports) == 2
    assert all(
        not {item["exit_time"] for item in report["test_trades"]}
        & {item["exit_time"] for item in report["in_sample"]}
        for report in reports
    )
