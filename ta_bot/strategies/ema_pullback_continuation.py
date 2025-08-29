"""
EMA Pullback Continuation Strategy
Adapted from Quantzed Screenings 11 & 12: "PONTO CONTÍNUO" strategies

Detects pullback opportunities in trending markets where price
briefly touches key EMAs before continuing the trend.
"""

from typing import Any, Dict, Optional

import pandas as pd

from ta_bot.models.signal import Signal
from ta_bot.strategies.base_strategy import BaseStrategy


class EMAPullbackContinuationStrategy(BaseStrategy):
    """
    EMA Pullback Continuation Strategy

    Bullish Setup (Screening 11):
        - Low touches or approaches EMA20
        - EMA20 > EMA30 (uptrend confirmation)
        - Price consistently above EMA20 for last 4 periods

    Bearish Setup (Screening 12):
        - High touches or approaches EMA20
        - EMA9 < EMA20 (downtrend confirmation)
        - Current high > previous high (failed breakout)
        - Price consistently below EMA20 for last 4 periods

    Risk Management:
        - Entry: Current high/low
        - Stop: Opposite extreme
        - Target: 2:1 risk-reward ratio

    Adapted from Quantzed Brazilian market screening strategies.
    """

    def analyze(
        self,
        df: pd.DataFrame,
        metadata: Dict[str, Any],
    ) -> Optional[Signal]:
        """Analyze for EMA pullback continuation signals."""
        if len(df) < 80:  # Need sufficient data for EMAs
            return None

        # Extract indicators from metadata
        indicators = {
            k: v for k, v in metadata.items() if k not in ["symbol", "timeframe"]
        }
        symbol = metadata.get("symbol", "UNKNOWN")
        timeframe = metadata.get("timeframe", "15m")

        # Calculate EMAs if not provided
        if "ema9" not in indicators:
            indicators["ema9"] = (
                df["close"].ewm(span=9, min_periods=8, adjust=True).mean()
            )
        if "ema20" not in indicators:
            indicators["ema20"] = (
                df["close"].ewm(span=20, min_periods=19, adjust=True).mean()
            )
        if "ema30" not in indicators:
            indicators["ema30"] = (
                df["close"].ewm(span=30, min_periods=29, adjust=True).mean()
            )

        current = self._get_current_values(indicators, df)

        # Check if we have all required indicators and price data
        required_indicators = ["ema9", "ema20", "ema30", "close", "high", "low"]
        if not all(indicator in current for indicator in required_indicators):
            return None

        # Need previous candle data
        if len(df) < 2:
            return None

        # Extract values
        current_close = current["close"]
        current_high = current["high"]
        current_low = current["low"]
        ema9 = current["ema9"]
        ema20 = current["ema20"]
        ema30 = current["ema30"]

        previous_high = float(df["high"].iloc[-2])

        # Check for bullish pullback setup (Quantzed Screening 11)
        bullish_trend = ema20 > ema30
        low_touches_ema20 = current_low <= ema20 * 1.01  # Within 1% of EMA20

        # Check if price was consistently above EMA20 for last 4 periods
        if len(df) >= 4:
            closes_last_4 = df["close"].iloc[-4:]
            ema20_series = indicators["ema20"]

            if isinstance(ema20_series, pd.Series) and len(ema20_series) >= 4:
                ema20_last_4 = ema20_series.iloc[-4:]
                bullish_trend_strength = all(
                    closes_last_4.iloc[i] > ema20_last_4.iloc[i] for i in range(4)
                )
            else:
                bullish_trend_strength = current_close > ema20
        else:
            bullish_trend_strength = current_close > ema20

        bullish_setup = bullish_trend and low_touches_ema20 and bullish_trend_strength

        # Check for bearish pullback setup (Quantzed Screening 12)
        bearish_trend = ema9 < ema20
        high_touches_ema20 = current_high >= ema20 * 0.99  # Within 1% of EMA20
        failed_breakout = current_high > previous_high

        # Check if price was consistently below EMA20 for last 4 periods
        if len(df) >= 4:
            closes_last_4 = df["close"].iloc[-4:]
            ema20_series = indicators["ema20"]

            if isinstance(ema20_series, pd.Series) and len(ema20_series) >= 4:
                ema20_last_4 = ema20_series.iloc[-4:]
                bearish_trend_strength = all(
                    closes_last_4.iloc[i] < ema20_last_4.iloc[i] for i in range(4)
                )
            else:
                bearish_trend_strength = current_close < ema20
        else:
            bearish_trend_strength = current_close < ema20

        bearish_setup = (
            bearish_trend
            and high_touches_ema20
            and failed_breakout
            and bearish_trend_strength
        )

        # Determine signal direction
        if bullish_setup:
            signal_action = "buy"
            entry_price = current_high
            stop_loss = current_low
            setup_type = "bullish_pullback"
            screening_origin = "quantzed_screening_11"
        elif bearish_setup:
            signal_action = "sell"
            entry_price = current_low
            stop_loss = current_high
            setup_type = "bearish_pullback"
            screening_origin = "quantzed_screening_12"
        else:
            return None

        # Calculate take profit using 2:1 risk-reward ratio
        risk_amount = abs(entry_price - stop_loss)
        if signal_action == "buy":
            take_profit = entry_price + (risk_amount * 2)
        else:
            take_profit = entry_price - (risk_amount * 2)

        # Calculate signal quality metrics
        ema_separation = abs(ema20 - ema30) / ema30 if ema30 > 0 else 0
        pullback_depth = abs(current_close - ema20) / ema20 if ema20 > 0 else 0

        # Better signal when EMAs are well separated (strong trend) and pullback is shallow
        trend_quality = min(1, ema_separation * 20)  # Normalize
        pullback_quality = max(0, 1 - (pullback_depth * 10))  # Prefer shallow pullbacks

        # Base confidence with quality adjustments
        base_confidence = 0.74
        trend_adjustment = trend_quality * 0.08  # Up to 8% boost
        pullback_adjustment = pullback_quality * 0.06  # Up to 6% boost

        final_confidence = min(
            0.88, base_confidence + trend_adjustment + pullback_adjustment
        )

        # Prepare metadata for signal
        signal_metadata = {
            "setup_type": setup_type,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_reward_ratio": 2.0,
            "ema9": ema9,
            "ema20": ema20,
            "ema30": ema30,
            "ema_separation": ema_separation,
            "pullback_depth": pullback_depth,
            "trend_quality": trend_quality,
            "pullback_quality": pullback_quality,
            "strategy_origin": screening_origin,
        }

        return Signal(
            strategy_id="ema_pullback_continuation",
            symbol=symbol,
            action=signal_action,
            confidence=final_confidence,
            current_price=current_close,
            price=entry_price,
            timeframe=timeframe,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata=signal_metadata,
        )
