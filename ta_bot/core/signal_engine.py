"""
Signal engine that coordinates all trading strategies.
"""

import pandas as pd
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ta_bot.models.signal import Signal, SignalType
from ta_bot.core.confidence import ConfidenceCalculator
from ta_bot.core.indicators import Indicators
from ta_bot.strategies.momentum_pulse import MomentumPulseStrategy
from ta_bot.strategies.band_fade_reversal import BandFadeReversalStrategy
from ta_bot.strategies.golden_trend_sync import GoldenTrendSyncStrategy
from ta_bot.strategies.range_break_pop import RangeBreakPopStrategy
from ta_bot.strategies.divergence_trap import DivergenceTrapStrategy

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
        """Analyze candles using all strategies and return signals."""
        signals: List[Signal] = []
        
        logger.info(f"=== Starting strategy analysis for {symbol} {period} ===")
        logger.info(f"DataFrame shape: {df.shape}, Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")

        # Calculate indicators
        logger.info("Calculating technical indicators...")
        indicators = self._calculate_indicators(df)
        
        # Log key indicator values
        latest_rsi = indicators["rsi"].iloc[-1] if not indicators["rsi"].empty else None
        latest_macd = indicators["macd"].iloc[-1] if not indicators["macd"].empty else None
        latest_adx = indicators["adx"].iloc[-1] if not indicators["adx"].empty else None
        logger.info(f"Latest indicators - RSI: {latest_rsi:.2f}, MACD: {latest_macd:.6f}, ADX: {latest_adx:.2f}")

        # Run each strategy
        for strategy_name, strategy in self.strategies.items():
            logger.info(f"--- Running {strategy_name} strategy ---")
            signal = self._run_strategy(
                strategy, strategy_name, df, symbol, period, indicators
            )
            if signal:
                signals.append(signal)
                logger.info(f"✅ {strategy_name}: SIGNAL GENERATED - {signal.signal.value} with {signal.confidence:.2f} confidence")
            else:
                logger.info(f"❌ {strategy_name}: No signal - conditions not met")

        logger.info(f"=== Strategy analysis complete: {len(signals)} signals generated ===")
        return signals

    def _calculate_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate all technical indicators for the dataframe."""
        indicators = {}

        # Basic indicators
        indicators["rsi"] = self.indicators.rsi(df)
        indicators["macd"], indicators["macd_signal"], indicators["macd_hist"] = (
            self.indicators.macd(df)
        )
        indicators["adx"] = self.indicators.adx(df)
        indicators["atr"] = self.indicators.atr(df)
        indicators["vwap"] = self.indicators.vwap(df)

        # EMAs
        indicators["ema21"] = self.indicators.ema(df, 21)
        indicators["ema50"] = self.indicators.ema(df, 50)
        indicators["ema200"] = self.indicators.ema(df, 200)

        # Bollinger Bands
        indicators["bb_lower"], indicators["bb_middle"], indicators["bb_upper"] = (
            self.indicators.bollinger_bands(df)
        )

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
    ) -> Optional[Signal]:
        """Run a single strategy and return signal if valid."""
        try:
            # Run strategy analysis
            signal_data = strategy.analyze(df, indicators)

            if not signal_data:
                logger.info(f"  {strategy_name}: No signal data returned by strategy")
                return None

            # Extract signal information
            signal_type = signal_data.get("signal_type", SignalType.BUY)
            metadata = signal_data.get("metadata", {})
            
            # Log strategy-specific details
            logger.info(f"  {strategy_name}: Signal type: {signal_type}")
            if metadata:
                logger.info(f"  {strategy_name}: Metadata: {metadata}")

            # Calculate confidence
            confidence = ConfidenceCalculator.calculate_confidence(
                strategy_name, df, metadata
            )
            logger.info(f"  {strategy_name}: Calculated confidence: {confidence:.2f}")

            # Create signal object
            signal = Signal(
                symbol=symbol,
                period=period,
                signal=signal_type,
                confidence=confidence,
                strategy=strategy_name,
                metadata=metadata,
                timestamp=datetime.utcnow().isoformat(),
            )

            # Validate signal
            if not signal.validate():
                logger.warning(f"  {strategy_name}: Invalid signal generated - validation failed")
                return None

            logger.info(f"  {strategy_name}: Signal validated successfully")
            return signal

        except Exception as e:
            logger.error(f"  {strategy_name}: Error during analysis: {e}")
            return None
