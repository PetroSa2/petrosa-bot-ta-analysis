# Trading Strategies

Detailed documentation for all technical analysis strategies implemented in the Petrosa TA Bot.

## 📊 Strategy Overview

The TA Bot implements 5 distinct trading strategies, each designed for different market conditions:

| Strategy | Type | Best Market | Confidence Base | Key Indicators |
|----------|------|-------------|-----------------|----------------|
| Momentum Pulse | Trend Following | Trending | 0.6 | MACD, RSI, EMAs |
| Band Fade Reversal | Mean Reversion | Ranging | 0.55 | Bollinger Bands, RSI |
| Golden Trend Sync | Trend Following | Strong Trends | 0.65 | EMAs, RSI, MACD |
| Range Break Pop | Breakout | Consolidation | 0.6 | ATR, Volume, RSI |
| Divergence Trap | Divergence | Reversal | 0.6 | RSI, Price Action |

## 🎯 Strategy 1: Momentum Pulse

### Overview
**Type**: Trend Following  
**Best For**: Trending markets with clear directional movement  
**Timeframe**: 15m, 1h  

### Logic
Identifies momentum shifts using MACD histogram crossovers with trend confirmation.

### Entry Conditions
```python
# Primary Trigger
macd_histogram_crosses_positive = macd_hist[-1] > 0 and macd_hist[-2] <= 0

# Confirmations
rsi_between_50_65 = 50 <= rsi[-1] <= 65
adx_above_20 = adx[-1] > 20
price_above_emas = close[-1] > ema21[-1] > ema50[-1]
```

### Exit Conditions
- **Stop Loss**: 2% below entry
- **Take Profit**: 3:1 risk-reward ratio
- **Time Stop**: 24 hours maximum

### Confidence Calculation
```python
base_confidence = 0.6

# RSI Bonus (if RSI < 60)
if rsi[-1] < 60:
    confidence += 0.1

# EMA Alignment Bonus
if ema21[-1] > ema50[-1] > ema200[-1]:
    confidence += 0.1

# ADX Strength Bonus
if adx[-1] > 30:
    confidence += 0.05
```

### Example Signal
```json
{
  "symbol": "BTCUSDT",
  "period": "15m",
  "signal": "BUY",
  "confidence": 0.75,
  "strategy": "momentum_pulse",
  "metadata": {
    "rsi": 58.3,
    "macd_hist": 0.0012,
    "adx": 27,
    "ema21": 50025.0,
    "ema50": 49980.0
  }
}
```

## 🎯 Strategy 2: Band Fade Reversal

### Overview
**Type**: Mean Reversion  
**Best For**: Ranging markets with clear support/resistance  
**Timeframe**: 15m, 1h  

### Logic
Captures reversals when price breaks out of Bollinger Bands and then returns inside.

### Entry Conditions
```python
# Primary Trigger
price_closes_outside_upper_bb = close[-2] > bb_upper[-2]
price_returns_inside = close[-1] <= bb_upper[-1]

# Confirmations
rsi_overbought = rsi[-1] > 70
adx_low_volatility = adx[-1] < 20
```

### Exit Conditions
- **Stop Loss**: Middle Bollinger Band
- **Take Profit**: Lower Bollinger Band
- **Time Stop**: 12 hours maximum

### Confidence Calculation
```python
base_confidence = 0.55

# RSI Overbought Bonus
if rsi[-1] > 75:
    confidence += 0.1

# Volatility Bonus
bb_width = (bb_upper[-1] - bb_lower[-1]) / bb_middle[-1]
if bb_width > 0.05:  # 5% band width
    confidence += 0.05
```

### Example Signal
```json
{
  "symbol": "BTCUSDT",
  "period": "15m",
  "signal": "SELL",
  "confidence": 0.65,
  "strategy": "band_fade_reversal",
  "metadata": {
    "rsi": 72.5,
    "bb_upper": 50200.0,
    "bb_middle": 50000.0,
    "bb_lower": 49800.0,
    "adx": 15
  }
}
```

## 🎯 Strategy 3: Golden Trend Sync

### Overview
**Type**: Trend Following  
**Best For**: Strong trending markets with pullbacks  
**Timeframe**: 1h, 4h  

### Logic
Identifies pullback entries in strong trends using EMA alignment and momentum confirmation.

### Entry Conditions
```python
# Primary Trigger
price_pulls_back_to_ema21 = abs(close[-1] - ema21[-1]) / ema21[-1] < 0.01

# Confirmations
ema_alignment = ema21[-1] > ema50[-1] > ema200[-1]
rsi_neutral = 45 <= rsi[-1] <= 55
macd_positive = macd_hist[-1] > 0
```

### Exit Conditions
- **Stop Loss**: EMA50 level
- **Take Profit**: 2:1 risk-reward ratio
- **Time Stop**: 48 hours maximum

### Confidence Calculation
```python
base_confidence = 0.65

# Trend Strength Bonus
ema_spread = (ema21[-1] - ema200[-1]) / ema200[-1]
if ema_spread > 0.02:  # 2% spread
    confidence += 0.1

# RSI Neutral Bonus
if 48 <= rsi[-1] <= 52:
    confidence += 0.05
```

### Example Signal
```json
{
  "symbol": "BTCUSDT",
  "period": "1h",
  "signal": "BUY",
  "confidence": 0.75,
  "strategy": "golden_trend_sync",
  "metadata": {
    "rsi": 49.8,
    "ema21": 50025.0,
    "ema50": 49980.0,
    "ema200": 49500.0,
    "macd_hist": 0.0008
  }
}
```

## 🎯 Strategy 4: Range Break Pop

### Overview
**Type**: Breakout  
**Best For**: Consolidation periods with low volatility  
**Timeframe**: 15m, 1h  

### Logic
Identifies breakouts from tight trading ranges with volume confirmation.

### Entry Conditions
```python
# Primary Trigger
tight_range = (high_10_period - low_10_period) / low_10_period < 0.025
breakout_up = close[-1] > high_10_period

# Confirmations
atr_falling = atr[-1] < atr[-5]
rsi_neutral = 45 <= rsi[-1] <= 55
volume_surge = volume[-1] > volume_avg * 1.5
```

### Exit Conditions
- **Stop Loss**: Range midpoint
- **Take Profit**: 1.5x range height
- **Time Stop**: 6 hours maximum

### Confidence Calculation
```python
base_confidence = 0.6

# Volume Surge Bonus
volume_ratio = volume[-1] / volume_avg
if volume_ratio > 2.0:
    confidence += 0.1

# Range Tightness Bonus
range_tightness = (high_10_period - low_10_period) / low_10_period
if range_tightness < 0.02:  # 2% range
    confidence += 0.05
```

### Example Signal
```json
{
  "symbol": "BTCUSDT",
  "period": "15m",
  "signal": "BUY",
  "confidence": 0.7,
  "strategy": "range_break_pop",
  "metadata": {
    "rsi": 51.2,
    "atr": 150.0,
    "volume_ratio": 2.1,
    "range_height": 200.0,
    "breakout_level": 50100.0
  }
}
```

## 🎯 Strategy 5: Divergence Trap

### Overview
**Type**: Divergence  
**Best For**: Market reversals and trend changes  
**Timeframe**: 1h, 4h  

### Logic
Identifies hidden bullish divergences where price makes higher lows but RSI makes lower lows.

### Entry Conditions
```python
# Primary Trigger
price_higher_low = low[-1] > low[-5]  # Price makes higher low
rsi_lower_low = rsi[-1] < rsi[-5]     # RSI makes lower low

# Confirmations
price_above_ema50 = close[-1] > ema50[-1]
macd_turning_up = macd_hist[-1] > macd_hist[-2]
```

### Exit Conditions
- **Stop Loss**: Recent swing low
- **Take Profit**: 2:1 risk-reward ratio
- **Time Stop**: 72 hours maximum

### Confidence Calculation
```python
base_confidence = 0.6

# Divergence Strength Bonus
price_change = (low[-1] - low[-5]) / low[-5]
rsi_change = (rsi[-5] - rsi[-1]) / rsi[-5]
divergence_strength = abs(price_change) + abs(rsi_change)
if divergence_strength > 0.1:  # 10% combined change
    confidence += 0.1

# MACD Confirmation Bonus
if macd_hist[-1] > 0:
    confidence += 0.05
```

### Example Signal
```json
{
  "symbol": "BTCUSDT",
  "period": "1h",
  "signal": "BUY",
  "confidence": 0.7,
  "strategy": "divergence_trap",
  "metadata": {
    "rsi": 45.2,
    "price_low": 49800.0,
    "rsi_low": 42.1,
    "macd_hist": 0.0005,
    "ema50": 49980.0
  }
}
```

## 🔧 Strategy Configuration

### Environment Variables
```bash
# Strategy-specific settings
RSI_PERIOD=14
MACD_FAST=12
MACD_SLOW=26
MACD_SIGNAL=9
ADX_PERIOD=14
BB_PERIOD=20
BB_STD=2.0
ATR_PERIOD=14
```

### Confidence Thresholds
```python
# Minimum confidence for signal generation
MIN_CONFIDENCE = 0.6

# Strategy-specific minimums
STRATEGY_MIN_CONFIDENCE = {
    'momentum_pulse': 0.65,
    'band_fade_reversal': 0.6,
    'golden_trend_sync': 0.7,
    'range_break_pop': 0.65,
    'divergence_trap': 0.65
}
```

## 📊 Strategy Performance Metrics

### Key Performance Indicators
- **Win Rate**: Percentage of profitable signals
- **Profit Factor**: Gross profit / Gross loss
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Sharpe Ratio**: Risk-adjusted returns
- **Average Hold Time**: Mean duration of positions

### Risk Management
- **Position Sizing**: Based on confidence and volatility
- **Stop Loss**: Dynamic based on ATR and support/resistance
- **Take Profit**: Risk-reward ratios from 1.5:1 to 3:1
- **Time Stops**: Prevent extended losing positions

## 🧪 Strategy Testing

### Backtesting Framework
```python
# Example backtest configuration
backtest_config = {
    'start_date': '2023-01-01',
    'end_date': '2023-12-31',
    'symbols': ['BTCUSDT', 'ETHUSDT'],
    'timeframes': ['15m', '1h'],
    'initial_capital': 10000,
    'commission': 0.001  # 0.1%
}
```

### Performance Validation
- **Walk-Forward Analysis**: Out-of-sample testing
- **Monte Carlo Simulation**: Random sampling of trades
- **Stress Testing**: Extreme market conditions
- **Parameter Optimization**: Grid search for optimal settings

## 🔄 Strategy Updates

### Adding New Strategies
1. Create strategy class inheriting from `BaseStrategy`
2. Implement `analyze()` method
3. Add confidence calculation in `ConfidenceCalculator`
4. Register strategy in `SignalEngine`
5. Add comprehensive tests

### Strategy Maintenance
- **Monthly Review**: Performance analysis and adjustments
- **Quarterly Optimization**: Parameter tuning based on recent data
- **Annual Overhaul**: Complete strategy re-evaluation

---

**Next Steps**:
- Read [Signal Engine](./SIGNAL_ENGINE.md) for core analysis engine details
- Check [API Reference](./API_REFERENCE.md) for signal output format
- Review [Architecture Overview](./ARCHITECTURE.md) for system design 