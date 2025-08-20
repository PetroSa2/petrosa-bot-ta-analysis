"""
Confidence calculation module for trading signals.
"""

from typing import Any, Dict

import pandas as pd


class ConfidenceCalculator:
    """Calculate confidence scores for trading signals."""

    @staticmethod
    def momentum_pulse_confidence(df: pd.DataFrame, metadata: Dict[str, Any]) -> float:
        """Calculate confidence for Momentum Pulse strategy."""
        base_confidence = 0.6

        # +0.1 if RSI < 60
        rsi = metadata.get("rsi", 0)
        if rsi < 60:
            base_confidence += 0.1

        # +0.1 if EMA21 > EMA50 > EMA200
        ema21 = metadata.get("ema21", 0)
        ema50 = metadata.get("ema50", 0)
        ema200 = metadata.get("ema200", 0)

        if ema21 > ema50 > ema200:
            base_confidence += 0.1

        return min(base_confidence, 1.0)

    @staticmethod
    def band_fade_reversal_confidence(
        df: pd.DataFrame, metadata: Dict[str, Any]
    ) -> float:
        """Calculate confidence for Band Fade Reversal strategy."""
        base_confidence = 0.55

        # +0.1 if RSI > 80
        rsi = metadata.get("rsi", 0)
        if rsi > 80:
            base_confidence += 0.1

        # +0.1 if candle wick > 1.5x average true range
        wick_ratio = metadata.get("wick_ratio", 0)
        atr = metadata.get("atr", 1)
        if wick_ratio > 1.5 * atr:
            base_confidence += 0.1

        return min(base_confidence, 1.0)

    @staticmethod
    def golden_trend_sync_confidence(
        df: pd.DataFrame, metadata: Dict[str, Any]
    ) -> float:
        """Calculate confidence for Golden Trend Sync strategy."""
        base_confidence = 0.65

        # +0.1 if price > VWAP
        price = metadata.get("close", 0)
        vwap = metadata.get("vwap", 0)
        if price > vwap:
            base_confidence += 0.1

        # +0.1 if bounce candle has highest volume in last 3
        volume_rank = metadata.get("volume_rank", 0)
        if volume_rank == 1:  # Highest volume in last 3 candles
            base_confidence += 0.1

        return min(base_confidence, 1.0)

    @staticmethod
    def range_break_pop_confidence(df: pd.DataFrame, metadata: Dict[str, Any]) -> float:
        """Calculate confidence for Range Break Pop strategy."""
        base_confidence = 0.6

        # +0.1 if volume > 2x average
        volume_ratio = metadata.get("volume_ratio", 0)
        if volume_ratio > 2.0:
            base_confidence += 0.1

        # +0.1 if MACD trending up
        macd_trend = metadata.get("macd_trend", 0)
        if macd_trend > 0:
            base_confidence += 0.1

        return min(base_confidence, 1.0)

    @staticmethod
    def divergence_trap_confidence(df: pd.DataFrame, metadata: Dict[str, Any]) -> float:
        """Calculate confidence for Divergence Trap strategy."""
        base_confidence = 0.6

        # +0.15 if recent trend up > 10% last 7 days
        trend_percent = metadata.get("trend_percent", 0)
        if trend_percent > 10:
            base_confidence += 0.15

        # +0.05 if candle has strong lower wick
        lower_wick = metadata.get("lower_wick", 0)
        if lower_wick > 0.6:  # Strong lower wick
            base_confidence += 0.05

        return min(base_confidence, 1.0)

    @staticmethod
    def calculate_confidence(
        strategy_name: str, df: pd.DataFrame, metadata: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for a given strategy."""
        confidence_methods = {
            "momentum_pulse": ConfidenceCalculator.momentum_pulse_confidence,
            "band_fade_reversal": ConfidenceCalculator.band_fade_reversal_confidence,
            "golden_trend_sync": ConfidenceCalculator.golden_trend_sync_confidence,
            "range_break_pop": ConfidenceCalculator.range_break_pop_confidence,
            "divergence_trap": ConfidenceCalculator.divergence_trap_confidence,
        }

        if strategy_name in confidence_methods:
            return confidence_methods[strategy_name](df, metadata)

        return 0.5  # Default confidence
