# Liquidity Grab Reversal Strategy - RSI Error Fix

**Date**: October 16, 2025
**Issue**: `KeyError: 'rsi'` in liquidity_grab_reversal strategy
**Status**: ✅ **FIXED**

---

## Problem Description

The `liquidity_grab_reversal` strategy was throwing a `KeyError: 'rsi'` during analysis:

```
2025-10-16 11:00:26.420 error  liquidity_grab_reversal: Error during analysis: 'rsi'
2025-10-16 11:00:18.934 error  liquidity_grab_reversal: Error during analysis: 'rsi'
```

### Root Cause

The error occurred in the `_check_rsi_divergence()` method at line 184:

```python
rsi_values = df["rsi"].iloc[-10:]
```

The method was attempting to access `rsi` as a column in the DataFrame, but:
- The DataFrame (`df`) only contains **OHLCV data** (open, high, low, close, volume)
- Technical indicators like RSI are calculated separately and passed via the `metadata` dictionary
- They are **not** added as columns to the DataFrame

### Architecture

```
SignalEngine._calculate_indicators()
  ↓ Calculates indicators as pandas Series
  ↓ indicators["rsi"] = self.indicators.rsi(df)
  ↓
SignalEngine._run_strategy()
  ↓ Passes indicators via metadata
  ↓ metadata = {**indicators, "symbol": symbol, "timeframe": period}
  ↓
Strategy.analyze(df, metadata)
  ↓ df contains only OHLCV
  ↓ metadata contains indicators + symbol + timeframe
```

## Solution

Modified the `_check_rsi_divergence()` method to accept the RSI series as a parameter instead of trying to access it from the DataFrame.

### Changes Made

**File**: `ta_bot/strategies/liquidity_grab_reversal.py`

1. **Updated method call** (line 72-74):
```python
# Before:
rsi_divergence = self._check_rsi_divergence(df, action)

# After:
rsi_divergence = self._check_rsi_divergence(
    df, action, indicators.get("rsi")
)
```

2. **Updated method signature** (line 180-182):
```python
# Before:
def _check_rsi_divergence(self, df: pd.DataFrame, action: str) -> bool:

# After:
def _check_rsi_divergence(
    self, df: pd.DataFrame, action: str, rsi_series: Optional[pd.Series] = None
) -> bool:
```

3. **Added validation** (line 187-193):
```python
# Check if RSI series is provided
if rsi_series is None or not isinstance(rsi_series, pd.Series):
    return False

# Ensure RSI series has enough data
if len(rsi_series) < 10:
    return False
```

4. **Updated RSI access** (line 196):
```python
# Before:
rsi_values = df["rsi"].iloc[-10:]

# After:
rsi_values = rsi_series.iloc[-10:]
```

## Verification

Created and ran a test script that:
1. ✅ Created test DataFrame with OHLCV data
2. ✅ Calculated RSI indicator as a pandas Series
3. ✅ Passed indicators via metadata (matching production behavior)
4. ✅ Successfully executed strategy without KeyError
5. ✅ Verified RSI divergence logic still works correctly

**Result**: `SUCCESS: Fix verified - no 'rsi' KeyError!`

## Impact

- **Immediate**: Fixes the production errors in liquidity_grab_reversal strategy
- **Scope**: Only affects the liquidity_grab_reversal strategy
- **Compatibility**: No breaking changes to strategy interface
- **Other Strategies**: Reviewed other strategies - they handle indicators correctly

## Best Practices

This fix reinforces the correct pattern for accessing indicators in strategies:

✅ **Correct Pattern**:
```python
def analyze(self, df: pd.DataFrame, metadata: Dict[str, Any]) -> Optional[Signal]:
    # Extract indicators from metadata
    indicators = {
        k: v for k, v in metadata.items() if k not in ["symbol", "timeframe"]
    }

    # Access indicators from the dictionary
    rsi_series = indicators.get("rsi")

    # Pass to helper methods
    result = self._helper_method(df, rsi_series)
```

❌ **Incorrect Pattern**:
```python
def _helper_method(self, df: pd.DataFrame) -> bool:
    # DON'T DO THIS - indicators are not in DataFrame
    rsi_values = df["rsi"].iloc[-10:]
```

## Related Files

- **Fixed**: `ta_bot/strategies/liquidity_grab_reversal.py`
- **Reference**: Other strategies that handle this correctly:
  - `ta_bot/strategies/divergence_trap.py` (line 46)
  - `ta_bot/strategies/rsi_extreme_reversal.py` (lines 62-80)

## Testing Recommendation

When testing strategies, ensure:
1. Indicators are passed via metadata (not in DataFrame)
2. DataFrame only contains OHLCV columns
3. Helper methods receive indicators as parameters
4. Validation checks for None/empty indicator series

---

**Status**: ✅ Fix applied, tested, and verified
**Next Steps**: Monitor production logs to confirm error resolution
