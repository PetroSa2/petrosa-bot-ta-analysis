"""
Band Fade Reversal Strategy
Detects mean reversion signals when price closes outside Bollinger Bands then back inside.
"""

from typing import Dict, Any, Optional
import pandas as pd
from ta_bot.models.signal import SignalType
from ta_bot.strategies.base_strategy import BaseStrategy


class BandFadeReversalStrategy(BaseStrategy):
    """
    Band Fade Reversal Strategy
    
    Trigger: Price closes outside upper BB(20, 2), then closes back inside
    Confirmations:
        - RSI(14) > 70
        - ADX(14) < 20
    """
    
    def analyze(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze for band fade reversal signals."""
        if len(df) < 3:
            return None
        
        current = self._get_current_values(indicators, df)
        previous = self._get_previous_values(indicators, df)
        
        # Check if we have all required indicators
        required_indicators = ['bb_upper', 'rsi', 'adx', 'close', 'atr']
        if not all(indicator in current for indicator in required_indicators):
            return None
        
        # Check if we have enough data for previous analysis
        if len(df) < 3:
            return None
        
        # Get values from 2 candles ago
        two_ago_close = float(df['close'].iloc[-3])
        two_ago_bb_upper = float(indicators['bb_upper'].iloc[-3])
        
        # Trigger: Price closes outside upper BB, then closes back inside
        # First: price was outside upper BB 2 candles ago
        was_outside = two_ago_close > two_ago_bb_upper
        
        # Second: current price is back inside upper BB
        is_inside = current['close'] <= current['bb_upper']
        
        bb_fade_trigger = was_outside and is_inside
        
        if not bb_fade_trigger:
            return None
        
        # Confirmations
        confirmations = []
        
        # RSI > 70
        rsi_ok = current['rsi'] > 70
        confirmations.append(('rsi_overbought', rsi_ok))
        
        # ADX < 20
        adx_ok = current['adx'] < 20
        confirmations.append(('adx_weak_trend', adx_ok))
        
        # Check if all confirmations are met
        all_confirmations = all(confirmation[1] for confirmation in confirmations)
        
        if not all_confirmations:
            return None
        
        # Calculate wick ratio for confidence
        wick_ratio = current.get('wick_ratio', 0)
        
        # Prepare metadata
        metadata = {
            'rsi': current['rsi'],
            'adx': current['adx'],
            'bb_upper': current['bb_upper'],
            'close': current['close'],
            'atr': current['atr'],
            'wick_ratio': wick_ratio,
            'confirmations': dict(confirmations)
        }
        
        return {
            'signal_type': SignalType.SELL,
            'metadata': metadata
        } 