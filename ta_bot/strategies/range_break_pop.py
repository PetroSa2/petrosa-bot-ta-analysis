"""
Range Break Pop Strategy
Detects volatility breakout signals when price breaks above a tight range.
"""

from typing import Dict, Any, Optional
import pandas as pd
from ta_bot.models.signal import SignalType
from ta_bot.strategies.base_strategy import BaseStrategy


class RangeBreakPopStrategy(BaseStrategy):
    """
    Range Break Pop Strategy
    
    Trigger: Price breaks above recent tight range (10 candles < 2.5% spread)
    Confirmations:
        - ATR(14) falling
        - RSI ~50
        - Breakout volume > 1.5x average
    """
    
    def analyze(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze for range break pop signals."""
        if len(df) < 12:
            return None
        
        current = self._get_current_values(indicators, df)
        previous = self._get_previous_values(indicators, df)
        
        # Check if we have all required indicators
        required_indicators = ['atr', 'rsi', 'close', 'volume']
        if not all(indicator in current for indicator in required_indicators):
            return None
        
        # Trigger: Price breaks above recent tight range
        # Check if we have a tight range in the last 10 candles
        recent_high = df['high'].iloc[-11:-1].max()  # Last 10 candles excluding current
        recent_low = df['low'].iloc[-11:-1].min()
        range_spread = (recent_high - recent_low) / recent_low * 100
        
        # Range should be tight (< 2.5% spread)
        if range_spread >= 2.5:
            return None
        
        # Current price should break above the recent high
        breakout_trigger = current['close'] > recent_high
        
        if not breakout_trigger:
            return None
        
        # Confirmations
        confirmations = []
        
        # ATR falling (current ATR < previous ATR)
        atr_falling = current['atr'] < previous['atr']
        confirmations.append(('atr_falling', atr_falling))
        
        # RSI around 50 (between 45-55)
        rsi_ok = self._check_between(current['rsi'], 45, 55)
        confirmations.append(('rsi_neutral', rsi_ok))
        
        # Breakout volume > 1.5x average
        avg_volume = df['volume'].iloc[-11:-1].mean()  # Average of last 10 candles
        volume_ratio = current['volume'] / avg_volume
        volume_ok = volume_ratio > 1.5
        confirmations.append(('volume_breakout', volume_ok))
        
        # Check if all confirmations are met
        all_confirmations = all(confirmation[1] for confirmation in confirmations)
        
        if not all_confirmations:
            return None
        
        # Check MACD trend for confidence
        macd_trend = 0
        if 'macd_hist' in current and 'macd_hist' in previous:
            macd_trend = current['macd_hist'] - previous['macd_hist']
        
        # Prepare metadata
        metadata = {
            'rsi': current['rsi'],
            'atr': current['atr'],
            'close': current['close'],
            'volume_ratio': volume_ratio,
            'range_spread': range_spread,
            'recent_high': recent_high,
            'macd_trend': macd_trend,
            'confirmations': dict(confirmations)
        }
        
        return {
            'signal_type': SignalType.BUY,
            'metadata': metadata
        } 