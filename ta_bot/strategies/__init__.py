"""
Trading strategies package for Petrosa TA Bot.

This package contains all trading strategies including:
- Original Petrosa strategies (11 strategies)
- Quantzed-adapted strategies (9 strategies)

Total: 20 comprehensive trading strategies covering all market conditions.
"""

from .band_fade_reversal import BandFadeReversalStrategy

# Additional Quantzed-adapted strategies
from .bear_trap_buy import BearTrapBuyStrategy
from .bear_trap_sell import BearTrapSellStrategy

# Quantzed-adapted strategies
from .bollinger_breakout_signals import BollingerBreakoutSignalsStrategy
from .bollinger_squeeze_alert import BollingerSqueezeAlertStrategy
from .divergence_trap import DivergenceTrapStrategy
from .doji_reversal import DojiReversalStrategy
from .ema_alignment_bearish import EMAAlignmentBearishStrategy
from .ema_alignment_bullish import EMAAlignmentBullishStrategy
from .ema_momentum_reversal import EMAMomentumReversalStrategy
from .ema_pullback_continuation import EMAPullbackContinuationStrategy
from .ema_slope_reversal_sell import EMASlopeReversalSellStrategy
from .fox_trap_reversal import FoxTrapReversalStrategy
from .golden_trend_sync import GoldenTrendSyncStrategy
from .hammer_reversal_pattern import HammerReversalPatternStrategy
from .ichimoku_cloud_momentum import IchimokuCloudMomentumStrategy
from .inside_bar_breakout import InsideBarBreakoutStrategy
from .inside_bar_sell import InsideBarSellStrategy
from .liquidity_grab_reversal import LiquidityGrabReversalStrategy
from .mean_reversion_scalper import MeanReversionScalperStrategy
from .minervini_trend_template import MinerviniTrendTemplateStrategy
from .momentum_pulse import MomentumPulseStrategy
from .multi_timeframe_trend_continuation import MultiTimeframeTrendContinuationStrategy
from .order_flow_imbalance import OrderFlowImbalanceStrategy
from .range_break_pop import RangeBreakPopStrategy
from .rsi_extreme_reversal import RSIExtremeReversalStrategy
from .shooting_star_reversal import ShootingStarReversalStrategy
from .volume_surge_breakout import VolumeSurgeBreakoutStrategy

__all__ = [
    # Original Petrosa strategies
    "BandFadeReversalStrategy",
    "DivergenceTrapStrategy",
    "GoldenTrendSyncStrategy",
    "IchimokuCloudMomentumStrategy",
    "LiquidityGrabReversalStrategy",
    "MeanReversionScalperStrategy",
    "MomentumPulseStrategy",
    "MultiTimeframeTrendContinuationStrategy",
    "OrderFlowImbalanceStrategy",
    "RangeBreakPopStrategy",
    "VolumeSurgeBreakoutStrategy",
    # Quantzed-adapted strategies
    "BollingerBreakoutSignalsStrategy",
    "BollingerSqueezeAlertStrategy",
    "EMAAlignmentBullishStrategy",
    "EMAMomentumReversalStrategy",
    "EMAPullbackContinuationStrategy",
    "FoxTrapReversalStrategy",
    "HammerReversalPatternStrategy",
    "InsideBarBreakoutStrategy",
    "RSIExtremeReversalStrategy",
    # Additional Quantzed-adapted strategies
    "BearTrapBuyStrategy",
    "BearTrapSellStrategy",
    "DojiReversalStrategy",
    "EMAAlignmentBearishStrategy",
    "EMASlopeReversalSellStrategy",
    "InsideBarSellStrategy",
    "MinerviniTrendTemplateStrategy",
    "ShootingStarReversalStrategy",
]
