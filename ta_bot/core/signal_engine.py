"""
Signal engine that coordinates all trading strategies.
"""

import logging
from typing import Any, Optional

import pandas as pd

from ta_bot.core.indicators import Indicators
from ta_bot.models.signal import Signal, SignalStrength, SignalType
from ta_bot.strategies.band_fade_reversal import BandFadeReversalStrategy

# Additional Quantzed-adapted strategies
from ta_bot.strategies.bear_trap_buy import BearTrapBuyStrategy
from ta_bot.strategies.bear_trap_sell import BearTrapSellStrategy

# Quantzed-adapted strategies
from ta_bot.strategies.bollinger_breakout_signals import (
    BollingerBreakoutSignalsStrategy,
)
from ta_bot.strategies.bollinger_squeeze_alert import BollingerSqueezeAlertStrategy
from ta_bot.strategies.divergence_trap import DivergenceTrapStrategy
from ta_bot.strategies.doji_reversal import DojiReversalStrategy
from ta_bot.strategies.ema_alignment_bearish import EMAAlignmentBearishStrategy
from ta_bot.strategies.ema_alignment_bullish import EMAAlignmentBullishStrategy
from ta_bot.strategies.ema_momentum_reversal import EMAMomentumReversalStrategy
from ta_bot.strategies.ema_pullback_continuation import EMAPullbackContinuationStrategy
from ta_bot.strategies.ema_slope_reversal_sell import EMASlopeReversalSellStrategy
from ta_bot.strategies.fox_trap_reversal import FoxTrapReversalStrategy
from ta_bot.strategies.golden_trend_sync import GoldenTrendSyncStrategy
from ta_bot.strategies.hammer_reversal_pattern import HammerReversalPatternStrategy
from ta_bot.strategies.ichimoku_cloud_momentum import IchimokuCloudMomentumStrategy
from ta_bot.strategies.inside_bar_breakout import InsideBarBreakoutStrategy
from ta_bot.strategies.inside_bar_sell import InsideBarSellStrategy
from ta_bot.strategies.liquidity_grab_reversal import LiquidityGrabReversalStrategy
from ta_bot.strategies.mean_reversion_scalper import MeanReversionScalperStrategy
from ta_bot.strategies.minervini_trend_template import MinerviniTrendTemplateStrategy
from ta_bot.strategies.momentum_pulse import MomentumPulseStrategy
from ta_bot.strategies.multi_timeframe_trend_continuation import (
    MultiTimeframeTrendContinuationStrategy,
)
from ta_bot.strategies.order_flow_imbalance import OrderFlowImbalanceStrategy
from ta_bot.strategies.range_break_pop import RangeBreakPopStrategy
from ta_bot.strategies.rsi_extreme_reversal import RSIExtremeReversalStrategy
from ta_bot.strategies.shooting_star_reversal import ShootingStarReversalStrategy
from ta_bot.strategies.volume_surge_breakout import VolumeSurgeBreakoutStrategy

logger = logging.getLogger(__name__)


class SignalEngine:
    """Main signal engine that coordinates all trading strategies."""

    def __init__(self):
        """Initialize the signal engine with all strategies."""
        self.strategies = {
            # Original Petrosa strategies
            "momentum_pulse": MomentumPulseStrategy(),
            "band_fade_reversal": BandFadeReversalStrategy(),
            "golden_trend_sync": GoldenTrendSyncStrategy(),
            "range_break_pop": RangeBreakPopStrategy(),
            "divergence_trap": DivergenceTrapStrategy(),
            "volume_surge_breakout": VolumeSurgeBreakoutStrategy(),
            "mean_reversion_scalper": MeanReversionScalperStrategy(),
            "ichimoku_cloud_momentum": IchimokuCloudMomentumStrategy(),
            "liquidity_grab_reversal": LiquidityGrabReversalStrategy(),
            "multi_timeframe_trend_continuation": MultiTimeframeTrendContinuationStrategy(),
            "order_flow_imbalance": OrderFlowImbalanceStrategy(),
            # Quantzed-adapted strategies
            "ema_alignment_bullish": EMAAlignmentBullishStrategy(),
            "bollinger_squeeze_alert": BollingerSqueezeAlertStrategy(),
            "bollinger_breakout_signals": BollingerBreakoutSignalsStrategy(),
            "rsi_extreme_reversal": RSIExtremeReversalStrategy(),
            "inside_bar_breakout": InsideBarBreakoutStrategy(),
            "ema_pullback_continuation": EMAPullbackContinuationStrategy(),
            "ema_momentum_reversal": EMAMomentumReversalStrategy(),
            "fox_trap_reversal": FoxTrapReversalStrategy(),
            "hammer_reversal_pattern": HammerReversalPatternStrategy(),
            # Additional Quantzed-adapted strategies
            "bear_trap_buy": BearTrapBuyStrategy(),
            "inside_bar_sell": InsideBarSellStrategy(),
            "shooting_star_reversal": ShootingStarReversalStrategy(),
            "doji_reversal": DojiReversalStrategy(),
            "ema_alignment_bearish": EMAAlignmentBearishStrategy(),
            "ema_slope_reversal_sell": EMASlopeReversalSellStrategy(),
            "minervini_trend_template": MinerviniTrendTemplateStrategy(),
            "bear_trap_sell": BearTrapSellStrategy(),
        }
        self.indicators = Indicators()

    def analyze_candles(
        self,
        df: pd.DataFrame,
        symbol: str,
        period: str,
        enabled_strategies: list[str] | None = None,
        min_confidence: float | None = None,
        max_confidence: float | None = None,
    ) -> list[Signal]:
        """
        Analyze candle data and generate trading signals.

        Args:
            df: DataFrame with OHLCV data
            symbol: Trading symbol (e.g., 'BTCUSDT')
            period: Timeframe (e.g., '5m', '15m')
            enabled_strategies: Optional list of strategy IDs to run (filters strategies)
            min_confidence: Optional minimum confidence threshold for signals
            max_confidence: Optional maximum confidence threshold for signals

        Returns:
            List of trading signals
        """
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

        # Determine which strategies to run
        strategies_to_run = self.strategies
        if enabled_strategies:
            # Filter to only enabled strategies
            strategies_to_run = {
                name: strategy
                for name, strategy in self.strategies.items()
                if name in enabled_strategies
            }
            logger.info(
                f"Running {len(strategies_to_run)} enabled strategies (out of {len(self.strategies)} total)"
            )
        else:
            logger.info(f"Running all {len(strategies_to_run)} strategies")

        signals = []

        # Run each strategy
        for strategy_name, strategy in strategies_to_run.items():
            logger.info(f"--- Running {strategy_name} strategy ---")
            signal = self._run_strategy(
                strategy, strategy_name, df, symbol, period, indicators, current_price
            )
            if signal:
                # Apply confidence filtering if specified
                if min_confidence is not None and signal.confidence < min_confidence:
                    logger.info(
                        f"❌ {strategy_name}: Signal filtered (confidence {signal.confidence:.2f} < min {min_confidence:.2f})"
                    )
                    continue
                if max_confidence is not None and signal.confidence > max_confidence:
                    logger.info(
                        f"❌ {strategy_name}: Signal filtered (confidence {signal.confidence:.2f} > max {max_confidence:.2f})"
                    )
                    continue

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

    def _calculate_indicators(self, df: pd.DataFrame) -> dict[str, Any]:
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
        indicators: dict[str, Any],
        current_price: float,
    ) -> Signal | None:
        """Run a single strategy and return signal if valid."""
        try:
            # Prepare metadata for strategy - pass indicators directly
            metadata = {**indicators, "symbol": symbol, "timeframe": period}
            # Run strategy analysis
            signal = strategy.analyze(df, metadata)

            if not signal:
                logger.info(f"  {strategy_name}: No signal returned by strategy")
                return None

            # Log strategy-specific details
            logger.info(f"  {strategy_name}: Signal type: {signal.action}")
            if signal.metadata:
                logger.info(f"  {strategy_name}: Metadata: {signal.metadata}")

            # CRITICAL FIX: Ensure all signals have stop_loss and take_profit
            # If strategy didn't set them, calculate using risk management
            if signal.stop_loss is None or signal.take_profit is None:
                logger.info(
                    f"  {strategy_name}: Calculating missing TP/SL using risk management"
                )

                # Map signal action to SignalType for risk management calculation
                signal_type = (
                    SignalType.BUY if signal.action == "buy" else SignalType.SELL
                )

                # Calculate TP/SL based on ATR and price action
                stop_loss, take_profit = self._calculate_risk_management(
                    current_price, indicators, signal_type
                )

                # Update signal with calculated values
                signal.stop_loss = stop_loss
                signal.take_profit = take_profit

                # Also add to metadata for transparency
                if signal.metadata is None:
                    signal.metadata = {}
                signal.metadata["stop_loss_calculated"] = True
                signal.metadata["stop_loss"] = stop_loss
                signal.metadata["take_profit"] = take_profit

                logger.info(
                    f"  {strategy_name}: Calculated TP/SL - SL: {stop_loss:.2f}, TP: {take_profit:.2f}"
                )
            else:
                logger.info(
                    f"  {strategy_name}: Using strategy-defined TP/SL - SL: {signal.stop_loss:.2f}, TP: {signal.take_profit:.2f}"
                )

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
        self, current_price: float, indicators: dict[str, Any], signal_type: SignalType
    ) -> tuple[float | None, float | None]:
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
