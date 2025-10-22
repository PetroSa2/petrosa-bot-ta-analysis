# TP/SL Fix Summary

## Problem
Positions were being sent without any Take Profit (TP) or Stop Loss (SL) orders. Some trading strategies were not setting these critical risk management parameters when generating signals, resulting in positions without proper exit strategies.

## Root Cause
The `SignalEngine` had a `_calculate_risk_management()` method for calculating TP/SL levels, but it was **never being called** in the signal generation flow. This meant:

1. **Strategies that set TP/SL manually** (like `momentum_pulse`, `golden_trend_sync`, etc.) worked fine
2. **Strategies that didn't set TP/SL** (like `rsi_extreme_reversal`, etc.) sent signals without risk management

## Solution
Modified the `_run_strategy()` method in `SignalEngine` to automatically calculate TP/SL values for any signal that doesn't have them set:

### Changes Made

#### 1. `ta_bot/core/signal_engine.py`
- Added automatic TP/SL calculation after strategy analysis
- If a signal has `stop_loss=None` or `take_profit=None`, the engine now:
  - Calls `_calculate_risk_management()` with current price, indicators, and signal type
  - Sets the calculated TP/SL values on the signal
  - Adds metadata flag `stop_loss_calculated=True` for transparency
- Signals with existing TP/SL values are left unchanged

#### 2. `ta_bot/config.py`
- Added configurable TP/SL parameters:
  - `default_stop_loss_pct`: Default stop loss percentage (default: 2%)
  - `default_take_profit_pct`: Default take profit percentage (default: 5%)
  - `atr_stop_loss_multiplier`: ATR multiplier for stop loss (default: 2.0)
  - `atr_take_profit_multiplier`: ATR multiplier for take profit (default: 3.0)

### Risk Management Logic

The `_calculate_risk_management()` method uses:

1. **ATR-based calculation** (if ATR is available):
   - Stop Loss: `current_price ± (ATR × 2)`
   - Take Profit: `current_price ± (ATR × 3)`
   - Risk/Reward Ratio: ~1.5:1

2. **Percentage-based fallback** (if ATR is not available):
   - Stop Loss: `current_price ± 2%`
   - Take Profit: `current_price ± 5%`
   - Risk/Reward Ratio: 2.5:1

3. **Direction-based logic**:
   - **BUY signals**: SL below entry, TP above entry
   - **SELL signals**: SL above entry, TP below entry

## Testing

### Verification Tests
Created comprehensive tests to verify the fix:

1. **Test 1**: Signal without TP/SL → Engine calculates them
   - ✅ PASSED: TP/SL automatically calculated
   - ✅ Metadata flag `stop_loss_calculated=True` added
   - ✅ Risk/Reward ratio appropriate

2. **Test 2**: Signal with TP/SL → Engine keeps original values
   - ✅ PASSED: Original TP/SL values preserved
   - ✅ No metadata flag added (not recalculated)
   - ✅ Strategy-defined values respected

### Existing Test Suite
- All 114 existing tests passed
- No breaking changes introduced
- Backward compatibility maintained

## Configuration

You can customize TP/SL calculation via environment variables:

```bash
# Default percentage-based TP/SL (used when ATR is not available)
DEFAULT_STOP_LOSS_PCT=0.02      # 2% stop loss
DEFAULT_TAKE_PROFIT_PCT=0.05    # 5% take profit

# ATR multipliers (used when ATR is available)
ATR_STOP_LOSS_MULTIPLIER=2.0    # 2x ATR for stop loss
ATR_TAKE_PROFIT_MULTIPLIER=3.0  # 3x ATR for take profit
```

## Impact

### Before Fix
- Some signals sent without TP/SL
- Positions opened without exit strategy
- Risk management incomplete

### After Fix
- **ALL signals now have TP/SL** (100% coverage)
- Positions always have exit strategy
- Risk management enforced at engine level
- Strategies can still define custom TP/SL if needed

## Monitoring

When reviewing signal metadata:
- If `stop_loss_calculated=True`: Engine calculated TP/SL
- If this field is absent: Strategy set TP/SL directly

Example signal metadata:
```json
{
  "strategy_id": "rsi_extreme_reversal",
  "symbol": "BTCUSDT",
  "action": "buy",
  "price": 50000.00,
  "stop_loss": 49000.00,
  "take_profit": 52000.00,
  "metadata": {
    "stop_loss_calculated": true,
    "rsi_2": 15.3,
    ...
  }
}
```

## Files Modified
- `ta_bot/core/signal_engine.py` - Added TP/SL calculation logic
- `ta_bot/config.py` - Added TP/SL configuration parameters
- `docs/TPSL_FIX_SUMMARY.md` - This documentation

## Next Steps
1. Monitor signals in production to verify TP/SL coverage
2. Adjust default TP/SL parameters based on performance metrics
3. Consider adding per-strategy TP/SL configuration in future

## Date
October 22, 2025
