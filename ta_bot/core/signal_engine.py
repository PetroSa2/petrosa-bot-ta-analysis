"""
Signal engine that coordinates all trading strategies.
"""

import pandas as pd
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ta_bot.models.signal import Signal, SignalType, SignalStrength, StrategyMode, OrderType, TimeInForce
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
        current_price = float(df['close'].iloc[-1])
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
                logger.info(f"✅ {strategy_name}: SIGNAL GENERATED - {signal.action} with {signal.confidence:.2f} confidence")
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
        current_price: float,
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

            # Determine signal strength based on confidence
            strength = self._calculate_signal_strength(confidence)
            
            # Calculate risk management parameters
            stop_loss, take_profit = self._calculate_risk_management(current_price, indicators, signal_type)

            # Create signal object with new format
            signal = Signal(
                strategy_id=f"{strategy_name}_{period}",
                strategy_mode=StrategyMode.DETERMINISTIC,
                symbol=symbol,
                action=signal_type.value,  # Convert enum to string
                confidence=confidence,
                strength=strength,
                current_price=current_price,
                price=current_price,
                quantity=0.0,  # Will be calculated by trade engine
                source="ta_bot",
                strategy=strategy_name,
                metadata=metadata,
                timeframe=period,
                order_type=OrderType.MARKET,
                time_in_force=TimeInForce.GTC,
                position_size_pct=0.1,  # Default 10% position size
                stop_loss=stop_loss,
                take_profit=take_profit,
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

    def _calculate_risk_management(self, current_price: float, indicators: Dict[str, Any], signal_type: SignalType) -> tuple[Optional[float], Optional[float]]:
        """Calculate stop loss and take profit levels."""
        atr = indicators.get("atr", 0)
        
        if atr <= 0:
            # Default percentages if ATR is not available
            stop_loss_pct = 0.02  # 2%
            take_profit_pct = 0.05  # 5%
        else:
            # Use ATR for dynamic levels
            stop_loss_pct = (atr * 2) / current_price  # 2x ATR
            take_profit_pct = (atr * 3) / current_price  # 3x ATR
        
        if signal_type == SignalType.BUY:
            stop_loss = current_price * (1 - stop_loss_pct)
            take_profit = current_price * (1 + take_profit_pct)
        else:  # SELL
            stop_loss = current_price * (1 + stop_loss_pct)
            take_profit = current_price * (1 - take_profit_pct)
        
        return stop_loss, take_profit
