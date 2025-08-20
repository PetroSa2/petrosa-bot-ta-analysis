"""
Signal engine that coordinates all trading strategies.
"""

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from ta_bot.core.indicators import Indicators
from ta_bot.models.signal import Signal, SignalStrength, SignalType
from ta_bot.strategies.band_fade_reversal import BandFadeReversalStrategy
from ta_bot.strategies.divergence_trap import DivergenceTrapStrategy
from ta_bot.strategies.golden_trend_sync import GoldenTrendSyncStrategy
from ta_bot.strategies.momentum_pulse import MomentumPulseStrategy
from ta_bot.strategies.range_break_pop import RangeBreakPopStrategy

logger = logging.getLogger(__name__)


class SignalEngine:
    """Main signal engine that coordinates all trading strategies."""

    def __init__(self):
        """Initialize the signal engine with all strategies."""
        self.strategies = {
            "momentum_pulse": MomentumPulseStrategy(),
            "band_fade_reversal": BandFadeReversalStrategy(),
            "golden_trend_sync": GoldenTrendSyncStrategy(),
            "range_break_pop": RangeBreakPopStrategy(),
            "divergence_trap": DivergenceTrapStrategy(),
        }
        self.indicators = Indicators()

    def analyze_candles(
        self, df: pd.DataFrame, symbol: str, period: str
    ) -> List[Signal]:
        """Analyze candle data and generate trading signals."""
        if df is None or len(df) == 0:
            logger.warning("No candle data provided for analysis")
            return []

        logger.info(f"=== Starting signal analysis for {symbol} {period} ===")
        logger.info(f"Dataframe shape: {df.shape}")

        # Calculate all technical indicators
        indicators = self._calculate_indicators(df)
        logger.info(f"Calculated {len(indicators)} technical indicators")

        # Get current price from the latest candle
        current_price = float(df["close"].iloc[-1])
        logger.info(f"Current price: {current_price}")

        signals = []

        # Run each strategy
        for strategy_name, strategy in self.strategies.items():
            logger.info(f"--- Running {strategy_name} strategy ---")
            signal = self._run_strategy(
                strategy, strategy_name, df, symbol, period, indicators, current_price
            )
            if signal:
                signals.append(signal)
                logger.info(
                    f"✅ {strategy_name}: SIGNAL GENERATED - {signal.action} with {signal.confidence:.2f} confidence"
                )
            else:
                logger.info(f"❌ {strategy_name}: No signal - conditions not met")

        logger.info(
            f"=== Strategy analysis complete: {len(signals)} signals generated ==="
        )
        return signals

    def _calculate_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate all technical indicators for the dataframe."""
        indicators = {}

        # Basic indicators
        indicators["rsi"] = self.indicators.rsi(df)
        (
            indicators["macd"],
            indicators["macd_signal"],
            indicators["macd_hist"],
        ) = self.indicators.macd(df)
        indicators["adx"] = self.indicators.adx(df)
        indicators["atr"] = self.indicators.atr(df)
        indicators["vwap"] = self.indicators.vwap(df)

        # EMAs
        indicators["ema21"] = self.indicators.ema(df, 21)
        indicators["ema50"] = self.indicators.ema(df, 50)
        indicators["ema200"] = self.indicators.ema(df, 200)

        # Bollinger Bands
        (
            indicators["bb_lower"],
            indicators["bb_middle"],
            indicators["bb_upper"],
        ) = self.indicators.bollinger_bands(df)

        # Volume indicators
        indicators["volume_sma"] = self.indicators.volume_sma(df)

        # Candle analysis
        indicators["wick_ratio"] = self.indicators.candle_wick_ratio(df)

        return indicators

    def _run_strategy(
        self,
        strategy,
        strategy_name: str,
        df: pd.DataFrame,
        symbol: str,
        period: str,
        indicators: Dict[str, Any],
        current_price: float,
    ) -> Optional[Signal]:
        """Run a single strategy and return signal if valid."""
        try:
            # Prepare metadata for strategy
            metadata = {"indicators": indicators, "symbol": symbol, "timeframe": period}
            # Run strategy analysis
            signal = strategy.analyze(df, metadata)

            if not signal:
                logger.info(f"  {strategy_name}: No signal returned by strategy")
                return None

            # Log strategy-specific details
            logger.info(f"  {strategy_name}: Signal type: {signal.action}")
            if signal.metadata:
                logger.info(f"  {strategy_name}: Metadata: {signal.metadata}")

            # Validate signal
            if not signal.validate():
                logger.warning(
                    f"  {strategy_name}: Invalid signal generated - validation failed"
                )
                return None

            logger.info(f"  {strategy_name}: Signal validated successfully")
            return signal

        except Exception as e:
            logger.error(f"  {strategy_name}: Error during analysis: {e}")
            return None

    def _calculate_signal_strength(self, confidence: float) -> SignalStrength:
        """Calculate signal strength based on confidence."""
        if confidence >= 0.8:
            return SignalStrength.EXTREME
        elif confidence >= 0.7:
            return SignalStrength.STRONG
        elif confidence >= 0.6:
            return SignalStrength.MEDIUM
        else:
            return SignalStrength.WEAK

    def _calculate_risk_management(
        self, current_price: float, indicators: Dict[str, Any], signal_type: SignalType
    ) -> tuple[Optional[float], Optional[float]]:
        """Calculate stop loss and take profit levels."""
        atr = indicators.get("atr", 0)

        # Handle case where ATR might be a pandas Series
        if isinstance(atr, pd.Series):
            if atr.empty or len(atr) == 0:
                atr_value = 0
            else:
                atr_value = float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else 0
        else:
            atr_value = float(atr) if atr is not None else 0

        if atr_value <= 0:
            # Default percentages if ATR is not available
            stop_loss_pct = 0.02  # 2%
            take_profit_pct = 0.05  # 5%
        else:
            # Use ATR for dynamic levels
            stop_loss_pct = (atr_value * 2) / current_price  # 2x ATR
            take_profit_pct = (atr_value * 3) / current_price  # 3x ATR

        if signal_type == SignalType.BUY:
            stop_loss = current_price * (1 - stop_loss_pct)
            take_profit = current_price * (1 + take_profit_pct)
        else:  # SELL
            stop_loss = current_price * (1 + stop_loss_pct)
            take_profit = current_price * (1 - take_profit_pct)

        return stop_loss, take_profit
