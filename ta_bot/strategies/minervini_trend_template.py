"""
Minervini Trend Template Strategy

Adapted from Quantzed's screening_35 'MODELO MINERVINI'.

This strategy implements Mark Minervini's Trend Template criteria for identifying
high-probability buy opportunities in strong uptrending assets:

1. Price > SMA50 > SMA150 > SMA200 (uptrend hierarchy)
2. SMA150 > SMA200 (trend consistency)
3. SMA200 trending up for at least 20 periods (long-term uptrend)
4. SMA50 > SMA150 and SMA50 > SMA200 (short-term strength)
5. Price >= 30% above 52-week low (recovery from base)
6. Price >= 75% of 52-week high (near highs)
7. Relative Strength Rating > 70 (outperforming market)

This is a comprehensive trend-following strategy that identifies assets
with institutional-quality momentum characteristics.
"""

from datetime import datetime
from typing import Optional

import pandas as pd

from ta_bot.models.signal import Signal, SignalStrength, SignalType
from ta_bot.strategies.base_strategy import BaseStrategy


class MinerviniTrendTemplateStrategy(BaseStrategy):
    """
    Minervini Trend Template Strategy

    Implements Mark Minervini's comprehensive trend template for identifying
    high-probability trend following opportunities with institutional characteristics.
    """

    def __init__(self):
        super().__init__()
        self.name = "Minervini Trend Template"
        self.description = (
            "Comprehensive trend following using Minervini's 7-point trend template"
        )
        self.min_periods = 265  # Need 260+ periods for 52-week calculations

    def analyze(self, data: pd.DataFrame, metadata: dict) -> Signal | None:
        """
        Analyze market data using Minervini's Trend Template criteria.

        Args:
            data: OHLCV DataFrame with datetime index
            metadata: Dictionary containing symbol, timeframe, and technical indicators

        Returns:
            Signal object if conditions are met, None otherwise
        """
        if len(data) < self.min_periods:
            return None

        try:
            # Extract symbol from metadata
            symbol = metadata.get("symbol", "UNKNOWN")

            closes = data["close"].astype(float)
            current_close = closes.iloc[-1]
            current_high = float(data["high"].iloc[-1])
            current_low = float(data["low"].iloc[-1])

            # Calculate Simple Moving Averages
            sma50 = closes.rolling(50).mean()
            sma150 = closes.rolling(150).mean()
            sma200 = closes.rolling(200).mean()

            if sma50.empty or sma150.empty or sma200.empty:
                return None

            current_sma50 = sma50.iloc[-1]
            current_sma150 = sma150.iloc[-1]
            current_sma200 = sma200.iloc[-1]

            # 52-week high and low (using 260 periods as proxy)
            week_52_low = closes.iloc[-260:].min()
            week_52_high = closes.iloc[-260:].max()

            # Calculate Relative Strength Rating (simplified version)
            # Compare performance over multiple timeframes
            if len(closes) >= 53:
                three_month_performance = (
                    current_close / closes.iloc[-63] if len(closes) >= 63 else 1.0
                )
                six_month_performance = (
                    current_close / closes.iloc[-126] if len(closes) >= 126 else 1.0
                )
                nine_month_performance = (
                    current_close / closes.iloc[-189] if len(closes) >= 189 else 1.0
                )
                twelve_month_performance = (
                    current_close / closes.iloc[-252] if len(closes) >= 252 else 1.0
                )

                # Weighted RS rating
                rs_rating = (
                    0.4 * three_month_performance
                    + 0.2 * six_month_performance
                    + 0.2 * nine_month_performance
                    + 0.2 * twelve_month_performance
                ) * 100
            else:
                rs_rating = 50  # Default neutral rating

            # Minervini's 7 Trend Template Criteria
            criteria = {
                # 1. Price > SMA50 > SMA150 > SMA200
                "uptrend_hierarchy": (
                    current_close > current_sma50
                    and current_sma50 > current_sma150
                    and current_sma150 > current_sma200
                ),
                # 2. SMA150 > SMA200
                "trend_consistency": current_sma150 > current_sma200,
                # 3. SMA200 trending up for at least 20 periods
                "long_term_uptrend": (
                    sma200.iloc[-1] > sma200.iloc[-21] if len(sma200) >= 21 else False
                ),
                # 4. SMA50 > SMA150 and SMA50 > SMA200
                "short_term_strength": (
                    current_sma50 > current_sma150 and current_sma50 > current_sma200
                ),
                # 5. Price >= 30% above 52-week low
                "recovery_from_base": current_close >= week_52_low * 1.30,
                # 6. Price >= 75% of 52-week high
                "near_highs": current_close >= week_52_high * 0.75,
                # 7. RS Rating > 70
                "relative_strength": rs_rating > 70,
            }

            # All criteria must be met
            all_criteria_met = all(criteria.values())

            if all_criteria_met:
                # Risk management
                entry_price = current_high  # Enter on breakout
                atr = self.indicators.atr(data, 14)
                if not atr.empty:
                    stop_distance = atr.iloc[-1] * 2  # 2x ATR stop
                else:
                    stop_distance = (
                        current_high - current_low
                    )  # Fallback to current range

                stop_loss = entry_price - stop_distance
                take_profit = entry_price + (stop_distance * 2)  # 1:2 risk/reward

                # Calculate confidence based on criteria strength
                criteria_score = sum([1 for c in criteria.values() if c]) / len(
                    criteria
                )
                rs_strength = min(1.0, (rs_rating - 70) / 30)  # Normalize RS above 70
                price_position = (current_close - week_52_low) / (
                    week_52_high - week_52_low
                )

                confidence = min(
                    0.90,
                    0.70
                    + (criteria_score * 0.10)
                    + (rs_strength * 0.05)
                    + (price_position * 0.05),
                )

                return Signal(
                    symbol=symbol,
                    strategy=self.name,
                    signal_type=SignalType.BUY,
                    strength=SignalStrength.HIGH,  # Comprehensive institutional-grade setup
                    confidence=confidence,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    timestamp=datetime.utcnow().isoformat(),
                    metadata={
                        "sma50": current_sma50,
                        "sma150": current_sma150,
                        "sma200": current_sma200,
                        "week_52_high": week_52_high,
                        "week_52_low": week_52_low,
                        "rs_rating": rs_rating,
                        "criteria_met": criteria,
                        "criteria_score": criteria_score,
                        "price_position_in_range": price_position,
                        "risk_reward_ratio": 2.0,
                        "pattern": "minervini_trend_template",
                    },
                )

        except Exception as e:
            self.logger.error(f"Error in {self.name} analysis: {e}")
            return None

        return None
