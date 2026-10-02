"""Point-in-time, cost-aware trade backtesting."""

from ta_bot.backtest.config import BacktestConfig
from ta_bot.backtest.simulator import BacktestResult, Trade, simulate

__all__ = ["BacktestConfig", "BacktestResult", "Trade", "simulate"]
