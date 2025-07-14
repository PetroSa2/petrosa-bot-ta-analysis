"""
Golden Trend Sync Strategy
Detects pullback entry signals when price pulls back to EMA21 with trend confirmations.
"""

from typing import Dict, Any, Optional
import pandas as pd
from ta_bot.models.signal import SignalType
from ta_bot.strategies.base_strategy import BaseStrategy


class GoldenTrendSyncStrategy(BaseStrategy):
    """
    Golden Trend Sync Strategy
    
    Trigger: Price pulls back to EMA21
    Confirmations:
        - EMA21 > EMA50 > EMA200
        - RSI between 45–55
        - MACD Histogram positive
    """
    
    def analyze(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze for golden trend sync signals."""
        if len(df) < 2:
            return None
        
        current = self._get_current_values(indicators, df)
        previous = self._get_previous_values(indicators, df)
        
        # Check if we have all required indicators
        required_indicators = ['ema21', 'ema50', 'ema200', 'rsi', 'macd_hist', 'close', 'vwap']
        if not all(indicator in current for indicator in required_indicators):
            return None
        
        # Trigger: Price pulls back to EMA21
        # Check if price is near EMA21 (within 0.5% of EMA21)
        ema21 = current['ema21']
        close = current['close']
        ema21_tolerance = ema21 * 0.005  # 0.5% tolerance
        
        price_near_ema21 = abs(close - ema21) <= ema21_tolerance
        
        if not price_near_ema21:
            return None
        
        # Confirmations
        confirmations = []
        
        # EMA21 > EMA50 > EMA200
        ema_trend_ok = (current['ema21'] > current['ema50'] > current['ema200'])
        confirmations.append(('ema_trend_aligned', ema_trend_ok))
        
        # RSI between 45-55
        rsi_ok = self._check_between(current['rsi'], 45, 55)
        confirmations.append(('rsi_neutral', rsi_ok))
        
        # MACD Histogram positive
        macd_positive = current['macd_hist'] > 0
        confirmations.append(('macd_positive', macd_positive))
        
        # Check if all confirmations are met
        all_confirmations = all(confirmation[1] for confirmation in confirmations)
        
        if not all_confirmations:
            return None
        
        # Calculate volume rank for confidence
        volume_rank = self._calculate_volume_rank(df)
        
        # Prepare metadata
        metadata = {
            'rsi': current['rsi'],
            'macd_hist': current['macd_hist'],
            'ema21': current['ema21'],
            'ema50': current['ema50'],
            'ema200': current['ema200'],
            'close': current['close'],
            'vwap': current['vwap'],
            'volume_rank': volume_rank,
            'confirmations': dict(confirmations)
        }
        
        return {
            'signal_type': SignalType.BUY,
            'metadata': metadata
        }
    
    def _calculate_volume_rank(self, df: pd.DataFrame) -> int:
        """Calculate volume rank of current candle compared to last 3 candles."""
        if len(df) < 4:
            return 0
        
        current_volume = df['volume'].iloc[-1]
        last_3_volumes = df['volume'].iloc[-4:-1]  # Last 3 candles excluding current
        
        # Count how many candles have higher volume than current
        higher_volume_count = (last_3_volumes > current_volume).sum()
        
        # Return rank (1 = highest, 4 = lowest)
        return higher_volume_count + 1 