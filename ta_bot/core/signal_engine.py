"""
Signal engine that coordinates all trading strategies.
"""

import pandas as pd
import logging
from typing import Dict, Any, List, Optional, Tuple
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
        """Analyze candles using all strategies and return valid signals."""
        signals = []

        try:
            # Ensure we have enough data for analysis
            if len(df) < 50:
                logger.warning(
                    f"Insufficient data for {symbol} {period}: {len(df)} candles"
                )
                return signals

            # Calculate all indicators once
            indicators_data = self._calculate_indicators(df)

            # Run each strategy
            for strategy_name, strategy in self.strategies.items():
                try:
                    signal = self._run_strategy(
                        strategy, strategy_name, df, symbol, period, indicators_data
                    )
                    if signal:
                        signals.append(signal)
                        logger.info(
                            f"Signal generated: {strategy_name} for {symbol} {period}"
                        )

                except Exception as e:
                    logger.error(f"Error running strategy {strategy_name}: {e}")
                    continue

            return signals

        except Exception as e:
            logger.error(f"Error in signal analysis for {symbol} {period}: {e}")
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
                return None

            # Extract signal information
            signal_type = signal_data.get("signal_type", SignalType.BUY)
            metadata = signal_data.get("metadata", {})

            # Calculate confidence
            confidence = ConfidenceCalculator.calculate_confidence(
                strategy_name, df, metadata
            )

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
                logger.warning(f"Invalid signal generated by {strategy_name}")
                return None

            return signal

        except Exception as e:
            logger.error(f"Error in strategy {strategy_name}: {e}")
            return None
