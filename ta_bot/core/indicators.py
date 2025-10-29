"""
Technical indicators wrapper using pandas-ta.
"""

import pandas as pd
import pandas_ta_classic as ta

from otel_init import get_tracer

# Ensure pandas DataFrame has ta attribute
pd.DataFrame.ta = ta

# Get tracer for manual spans
tracer = get_tracer("ta_bot.core.indicators")


class Indicators:
    """Wrapper for technical indicators using pandas-ta."""

    @staticmethod
    def rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate RSI indicator."""
        with tracer.start_as_current_span("calculate_rsi") as span:
            span.set_attribute("period", period)
            span.set_attribute("data_points", len(df))

            result = df.ta.rsi(close=df["close"], length=period)
            result_series = result if result is not None else pd.Series(dtype=float)

            # Add result info to span
            if not result_series.empty:
                span.set_attribute("rsi_value", float(result_series.iloc[-1]))

            return result_series

    @staticmethod
    def macd(
        df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD indicator."""
        with tracer.start_as_current_span("calculate_macd") as span:
            span.set_attribute("fast", fast)
            span.set_attribute("slow", slow)
            span.set_attribute("signal", signal)
            span.set_attribute("data_points", len(df))

            macd_result = df.ta.macd(
                close=df["close"], fast=fast, slow=slow, signal=signal
            )
            if macd_result is None or macd_result.empty:
                # Return empty series for insufficient data
                span.set_attribute("result", "insufficient_data")
                empty_series = pd.Series(dtype=float)
                return empty_series, empty_series, empty_series

            # Handle different column naming conventions between pandas-ta versions
            macd_col = f"MACD_{fast}_{slow}_{signal}"
            macds_col = (
                f"MACDS_{fast}_{slow}_{signal}"
                if f"MACDS_{fast}_{slow}_{signal}" in macd_result.columns
                else f"MACDs_{fast}_{slow}_{signal}"
            )
            macdh_col = (
                f"MACDH_{fast}_{slow}_{signal}"
                if f"MACDH_{fast}_{slow}_{signal}" in macd_result.columns
                else f"MACDh_{fast}_{slow}_{signal}"
            )

            macd_line = macd_result[macd_col]
            signal_line = macd_result[macds_col]
            histogram = macd_result[macdh_col]

            # Add result values to span
            if not macd_line.empty:
                span.set_attribute("macd_value", float(macd_line.iloc[-1]))
                span.set_attribute("signal_value", float(signal_line.iloc[-1]))
                span.set_attribute("histogram_value", float(histogram.iloc[-1]))

            return macd_line, signal_line, histogram

    @staticmethod
    def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate ADX indicator."""
        with tracer.start_as_current_span("calculate_adx") as span:
            span.set_attribute("period", period)
            span.set_attribute("data_points", len(df))

            adx_result = df.ta.adx(
                high=df["high"], low=df["low"], close=df["close"], length=period
            )
            if adx_result is None or adx_result.empty:
                span.set_attribute("result", "insufficient_data")
                return pd.Series(dtype=float)

            adx_series = adx_result["ADX_14"]
            if not adx_series.empty:
                span.set_attribute("adx_value", float(adx_series.iloc[-1]))

            return adx_series

    @staticmethod
    def bollinger_bands(
        df: pd.DataFrame, period: int = 20, std: float = 2.0
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands."""
        with tracer.start_as_current_span("calculate_bollinger_bands") as span:
            span.set_attribute("period", period)
            span.set_attribute("std_dev", std)
            span.set_attribute("data_points", len(df))

            bb_result = df.ta.bbands(close=df["close"], length=period, std=std)
            if bb_result is None or bb_result.empty:
                span.set_attribute("result", "insufficient_data")
                empty_series = pd.Series(dtype=float)
                return empty_series, empty_series, empty_series

            # Handle different column naming conventions between pandas-ta versions
            bbl_col = (
                f"BBL_{period}_{std}"
                if f"BBL_{period}_{std}" in bb_result.columns
                else f"BBL_{period}"
            )
            bbm_col = (
                f"BBM_{period}_{std}"
                if f"BBM_{period}_{std}" in bb_result.columns
                else f"BBM_{period}"
            )
            bbu_col = (
                f"BBU_{period}_{std}"
                if f"BBU_{period}_{std}" in bb_result.columns
                else f"BBU_{period}"
            )

            lower = bb_result[bbl_col]
            middle = bb_result[bbm_col]
            upper = bb_result[bbu_col]

            # Add values to span
            if not lower.empty:
                lower_val = float(lower.iloc[-1])
                upper_val = float(upper.iloc[-1])
                span.set_attribute("bb_lower", lower_val)
                span.set_attribute("bb_middle", float(middle.iloc[-1]))
                span.set_attribute("bb_upper", upper_val)
                span.set_attribute("bb_width", upper_val - lower_val)
                span.set_attribute("price_position", float(df["close"].iloc[-1]))

            return lower, middle, upper

    @staticmethod
    def ema(df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate EMA indicator."""
        result = df.ta.ema(close=df["close"], length=period)
        return result if result is not None else pd.Series(dtype=float)

    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        result = df.ta.atr(
            high=df["high"], low=df["low"], close=df["close"], length=period
        )
        return result if result is not None else pd.Series(dtype=float)

    @staticmethod
    def vwap(df: pd.DataFrame) -> pd.Series:
        """Calculate VWAP indicator."""
        try:
            return df.ta.vwap(
                high=df["high"], low=df["low"], close=df["close"], volume=df["volume"]
            )
        except AttributeError:
            # Fallback for non-datetime index
            typical_price = (df["high"] + df["low"] + df["close"]) / 3
            vwap = (typical_price * df["volume"]).cumsum() / df["volume"].cumsum()
            return vwap

    @staticmethod
    def volume_sma(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calculate Volume Simple Moving Average."""
        return df["volume"].rolling(window=period).mean()

    @staticmethod
    def price_range(df: pd.DataFrame, period: int = 10) -> pd.Series:
        """Calculate price range (high - low) over period."""
        return (df["high"] - df["low"]).rolling(window=period).mean()

    @staticmethod
    def candle_wick_ratio(df: pd.DataFrame) -> pd.Series:
        """Calculate candle wick ratio (body vs wick)."""
        body = abs(df["close"] - df["open"])
        total_range = df["high"] - df["low"]
        wick = total_range - body
        return wick / total_range

    @staticmethod
    def is_inside_candle(df: pd.DataFrame) -> pd.Series:
        """Check if current candle is inside the previous candle."""
        return (df["high"] <= df["high"].shift(1)) & (df["low"] >= df["low"].shift(1))

    @staticmethod
    def is_outside_candle(df: pd.DataFrame) -> pd.Series:
        """Check if current candle engulfs the previous candle."""
        return (df["high"] > df["high"].shift(1)) & (df["low"] < df["low"].shift(1))
