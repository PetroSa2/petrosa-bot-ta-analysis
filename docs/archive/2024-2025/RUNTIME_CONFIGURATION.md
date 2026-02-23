# Runtime Application Configuration

## Overview

The TA Bot now supports runtime configuration changes without requiring pod restarts. This allows you to dynamically adjust trading strategies, symbols, timeframes, confidence thresholds, and risk management parameters via a REST API.

## What's Runtime Configurable

### Strategy Settings
- **enabled_strategies**: List of strategy IDs to run
- **symbols**: Trading symbols to monitor (e.g., BTCUSDT, ETHUSDT)
- **candle_periods**: Timeframes to analyze (e.g., 5m, 15m, 1h)

### Confidence Thresholds
- **min_confidence**: Minimum signal confidence (0.0 to 1.0)
- **max_confidence**: Maximum signal confidence (0.0 to 1.0)

### Risk Management
- **max_positions**: Maximum concurrent positions
- **position_sizes**: Available position sizes

## Architecture

### Components

**AppConfigManager** (`ta_bot/services/app_config_manager.py`)
- Manages runtime configuration with dual persistence (MongoDB primary, MySQL fallback)
- 60-second cache TTL for performance
- Full audit trail of all changes
- Configuration validation

**API Routes** (`ta_bot/api/config_routes.py`)
- Consolidated configuration API at `/api/v1/config/*`
- Application config: `/api/v1/config/application`
- Strategy config: `/api/v1/strategies/{strategy_id}/config`

**Validation** (`ta_bot/services/app_config_validator.py`)
- Comprehensive validation rules
- Prevents invalid configurations
- Supports dry-run validation

### Data Flow

```
1. API Request → AppConfigManager
2. Validation → MongoDB/MySQL Persistence
3. Audit Trail Created
4. Cache Invalidated
5. Next NATS Message → Config Loaded
6. Signal Engine → Uses New Config
```

## API Usage

### Get Current Configuration

```bash
curl -X GET http://localhost:8000/api/v1/config/application
```

**Response:**
```json
{
  "success": true,
  "data": {
    "enabled_strategies": ["momentum_pulse", "rsi_extreme_reversal"],
    "symbols": ["BTCUSDT", "ETHUSDT"],
    "candle_periods": ["5m", "15m"],
    "min_confidence": 0.6,
    "max_confidence": 0.95,
    "max_positions": 10,
    "position_sizes": [100, 200, 500, 1000],
    "version": 2,
    "source": "mongodb",
    "created_at": "2025-10-17T10:00:00Z",
    "updated_at": "2025-10-21T14:00:00Z"
  },
  "metadata": {"cache_hit": true}
}
```

### Update Configuration

```bash
curl -X POST http://localhost:8000/api/v1/config/application \
  -H "Content-Type: application/json" \
  -d '{
    "enabled_strategies": ["momentum_pulse", "rsi_extreme_reversal", "bollinger_breakout_signals"],
    "symbols": ["BTCUSDT", "ETHUSDT"],
    "candle_periods": ["5m", "15m"],
    "min_confidence": 0.6,
    "max_confidence": 0.9,
    "changed_by": "admin",
    "reason": "Optimizing for volatile market conditions"
  }'
```

**Important**: All fields are optional - only provide fields you want to update.

### Validate Configuration (Dry Run)

```bash
curl -X POST http://localhost:8000/api/v1/config/application \
  -H "Content-Type: application/json" \
  -d '{
    "enabled_strategies": ["momentum_pulse"],
    "symbols": ["BTCUSDT"],
    "validate_only": true,
    "changed_by": "admin"
  }'
```

### View Change History

```bash
curl -X GET http://localhost:8000/api/v1/config/application/audit?limit=50
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "507f1f77bcf86cd799439013",
      "action": "UPDATE",
      "old_config": {
        "enabled_strategies": ["momentum_pulse"],
        "min_confidence": 0.7
      },
      "new_config": {
        "enabled_strategies": ["momentum_pulse", "rsi_extreme_reversal"],
        "min_confidence": 0.6
      },
      "changed_by": "admin",
      "changed_at": "2025-10-21T14:45:00Z",
      "reason": "Adding RSI strategy for diversification"
    }
  ]
}
```

### Force Cache Refresh

```bash
curl -X POST http://localhost:8000/api/v1/config/application/cache/refresh
```

## Validation Rules

### Enabled Strategies
- Must be non-empty list
- Each strategy must exist in the system
- Available strategies listed in `/api/v1/strategies`

### Symbols
- Must be non-empty list
- Format: uppercase, 6-12 characters
- Must end with quote currency (USDT, BUSD, BTC, ETH, BNB, USDC)
- Examples: BTCUSDT, ETHUSDT, ADAUSDT

### Candle Periods (Timeframes)
- Must be non-empty list
- Valid formats: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
- Examples: ["5m", "15m", "1h"]

### Confidence Thresholds
- 0.0 <= min_confidence < max_confidence <= 1.0
- Typical range: 0.5 to 0.95

### Risk Management
- max_positions: integer >= 1
- position_sizes: list of positive integers

## Configuration Priority

1. **Runtime Configuration** (MongoDB/MySQL)
   - Latest configuration from API
   - Takes precedence over startup config

2. **Startup Configuration** (`ta_bot/config.py`)
   - Loaded from environment variables
   - Used if no runtime config exists
   - Automatically persisted to database on first run

3. **Fallback Defaults**
   - Hardcoded defaults if database unavailable

## Graceful Configuration Application

Changes apply gradually and gracefully:

1. Configuration updated via API
2. Stored in MongoDB/MySQL
3. Cache invalidated (60s TTL)
4. **On next NATS message:**
   - Fresh config loaded from database
   - Symbol/timeframe filtering updated
   - Enabled strategies updated
   - Confidence thresholds applied

**No mid-processing interruption** - changes apply between message processing cycles.

## Monitoring

### Check Configuration Status

```bash
# Current configuration
GET /api/v1/config/application

# Check cache hit rate
# Look for "cache_hit": true in metadata

# View recent changes
GET /api/v1/config/application/audit?limit=10
```

### Logs

```bash
# Configuration loading
kubectl logs -f deployment/ta-bot -n petrosa-apps | grep "runtime config"

# Strategy filtering
kubectl logs -f deployment/ta-bot -n petrosa-apps | grep "enabled strategies"

# Confidence filtering
kubectl logs -f deployment/ta-bot -n petrosa-apps | grep "confidence"
```

## Examples

### Enable Only High-Confidence Strategies

```bash
curl -X POST http://localhost:8000/api/v1/config/application \
  -H "Content-Type: application/json" \
  -d '{
    "enabled_strategies": ["rsi_extreme_reversal", "bollinger_breakout_signals", "momentum_pulse"],
    "min_confidence": 0.75,
    "max_confidence": 0.95,
    "changed_by": "risk_manager",
    "reason": "Focusing on high-confidence signals during volatile market"
  }'
```

### Focus on Major Pairs Only

```bash
curl -X POST http://localhost:8000/api/v1/config/application \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["BTCUSDT", "ETHUSDT"],
    "candle_periods": ["15m", "1h"],
    "changed_by": "trader",
    "reason": "Focusing on major pairs with longer timeframes"
  }'
```

### Aggressive Trading Setup

```bash
curl -X POST http://localhost:8000/api/v1/config/application \
  -H "Content-Type: application/json" \
  -d '{
    "enabled_strategies": [
      "momentum_pulse",
      "rsi_extreme_reversal",
      "bollinger_breakout_signals",
      "volume_surge_breakout",
      "mean_reversion_scalper"
    ],
    "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT"],
    "candle_periods": ["5m", "15m"],
    "min_confidence": 0.5,
    "max_confidence": 0.95,
    "max_positions": 20,
    "changed_by": "aggressive_mode",
    "reason": "Aggressive trading configuration for high volatility"
  }'
```

### Conservative Trading Setup

```bash
curl -X POST http://localhost:8000/api/v1/config/application \
  -H "Content-Type: application/json" \
  -d '{
    "enabled_strategies": ["golden_trend_sync", "ichimoku_cloud_momentum"],
    "symbols": ["BTCUSDT", "ETHUSDT"],
    "candle_periods": ["1h", "4h"],
    "min_confidence": 0.8,
    "max_confidence": 0.95,
    "max_positions": 3,
    "changed_by": "conservative_mode",
    "reason": "Conservative configuration for stable trends"
  }'
```

## Troubleshooting

### Configuration Not Taking Effect

1. **Check cache TTL**: Wait up to 60 seconds for cache to expire
2. **Force refresh**: `POST /api/v1/config/application/cache/refresh`
3. **Check logs**: Look for "Loaded runtime config version" messages
4. **Verify MongoDB**: Ensure MongoDB is accessible

### Validation Errors

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Configuration validation failed",
    "details": {
      "errors": [
        "Symbol must be uppercase: btcusdt",
        "min_confidence must be less than max_confidence"
      ]
    }
  }
}
```

**Solution**: Fix validation errors and retry. Use `validate_only: true` for dry-run testing.

### Configuration Manager Not Initialized

```json
{
  "success": false,
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "Application configuration manager not initialized"
  }
}
```

**Solution**: Restart the TA Bot pod. Configuration manager initializes at startup.

## Best Practices

1. **Start Broad**: Begin with many strategies enabled, then optimize based on performance
2. **Use Audit Trail**: Track configuration changes and correlate with performance
3. **Test First**: Use `validate_only: true` to test configuration before applying
4. **Gradual Changes**: Make small, incremental changes and monitor impact
5. **Document Reasons**: Always provide meaningful `reason` field for audit trail
6. **Monitor Signals**: Watch signal generation rates after configuration changes
7. **Cache Refresh**: Force cache refresh when immediate changes are needed

## Integration with Existing Systems

### Environment Variables (Startup Only)
- `SUPPORTED_SYMBOLS`: Default symbols (overridden by runtime config)
- `SUPPORTED_TIMEFRAMES`: Default timeframes (overridden by runtime config)

### MongoDB Collections
- `app_config`: Single document with current configuration
- `app_config_audit`: Audit trail of all changes

### Configuration Files
- `ta_bot/config.py`: Startup configuration (fallback only)
- Runtime config always takes precedence

## API Documentation

Full API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

All endpoints are MCP-compatible and include detailed documentation for LLM agents.
