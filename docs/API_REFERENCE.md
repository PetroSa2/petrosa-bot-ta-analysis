# API Reference

Complete API documentation for the Petrosa TA Bot.

## 📋 Overview

The TA Bot provides a REST API for signal generation and health monitoring. The API is designed for internal use within the Petrosa trading ecosystem.

## 🔗 Base URL

```
Production: https://ta-bot.petrosa.com
Development: http://localhost:8000
```

## 🔐 Authentication

Currently, the API uses internal authentication within the Kubernetes cluster. No external authentication is required for internal services.

## 📊 Response Format

All API responses follow this standard format:

```json
{
  "status": "success|error",
  "data": {},
  "message": "Optional message",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 🏥 Health Endpoints

### GET /health

Get detailed health status of the TA Bot.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "build_info": {
    "commit_sha": "abc123...",
    "build_date": "2024-01-15T10:30:00Z"
  },
  "components": {
    "signal_engine": "running",
    "nats_listener": "connected",
    "publisher": "ready"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### GET /ready

Check if the service is ready to receive requests.

**Response:**
```json
{
  "status": "ready",
  "checks": {
    "nats_connection": "ok",
    "api_endpoint": "ok",
    "signal_engine": "ok"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### GET /live

Check if the service is alive (liveness probe).

**Response:**
```json
{
  "status": "alive",
  "uptime": "2h 30m 15s",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 📈 Signal Endpoints

### POST /signals

Generate trading signals based on provided candle data.

**Request Body:**
```json
{
  "symbol": "BTCUSDT",
  "period": "15m",
  "timestamp": 1640995200000,
  "open": 50000.0,
  "high": 50100.0,
  "low": 49900.0,
  "close": 50050.0,
  "volume": 1000.0
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "signals": [
      {
        "symbol": "BTCUSDT",
        "period": "15m",
        "signal": "BUY",
        "confidence": 0.74,
        "strategy": "momentum_pulse",
        "metadata": {
          "rsi": 58.3,
          "macd_hist": 0.0012,
          "adx": 27,
          "bollinger_position": 0.6,
          "atr": 150.0
        },
        "timestamp": "2024-01-15T10:30:00Z"
      }
    ],
    "processing_time": 0.045,
    "strategies_executed": 5
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### GET /signals/{symbol}

Get recent signals for a specific symbol.

**Parameters:**
- `symbol` (string): Trading symbol (e.g., "BTCUSDT")
- `limit` (optional, int): Number of signals to return (default: 10)
- `period` (optional, string): Timeframe filter (e.g., "15m", "1h")

**Response:**
```json
{
  "status": "success",
  "data": {
    "symbol": "BTCUSDT",
    "signals": [
      {
        "symbol": "BTCUSDT",
        "period": "15m",
        "signal": "BUY",
        "confidence": 0.74,
        "strategy": "momentum_pulse",
        "metadata": {
          "rsi": 58.3,
          "macd_hist": 0.0012,
          "adx": 27
        },
        "timestamp": "2024-01-15T10:30:00Z"
      }
    ],
    "total": 1,
    "period": "15m"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 📊 Metrics Endpoints

### GET /metrics

Get Prometheus-compatible metrics.

**Response:**
```
# HELP ta_bot_signals_generated_total Total signals generated
# TYPE ta_bot_signals_generated_total counter
ta_bot_signals_generated_total{strategy="momentum_pulse"} 15
ta_bot_signals_generated_total{strategy="band_fade_reversal"} 8

# HELP ta_bot_signal_confidence Signal confidence distribution
# TYPE ta_bot_signal_confidence histogram
ta_bot_signal_confidence_bucket{strategy="momentum_pulse",le="0.1"} 0
ta_bot_signal_confidence_bucket{strategy="momentum_pulse",le="0.5"} 2
ta_bot_signal_confidence_bucket{strategy="momentum_pulse",le="0.9"} 12
ta_bot_signal_confidence_bucket{strategy="momentum_pulse",le="+Inf"} 15

# HELP ta_bot_processing_time_seconds Signal processing time
# TYPE ta_bot_processing_time_seconds histogram
ta_bot_processing_time_seconds_bucket{le="0.01"} 5
ta_bot_processing_time_seconds_bucket{le="0.05"} 15
ta_bot_processing_time_seconds_bucket{le="0.1"} 20
ta_bot_processing_time_seconds_bucket{le="+Inf"} 25
```

## 🎯 Strategy Endpoints

### GET /strategies

Get list of available trading strategies.

**Response:**
```json
{
  "status": "success",
  "data": {
    "strategies": [
      {
        "name": "momentum_pulse",
        "description": "MACD histogram crossovers",
        "status": "active",
        "performance": {
          "signals_generated": 15,
          "avg_confidence": 0.72,
          "success_rate": 0.68
        }
      },
      {
        "name": "band_fade_reversal",
        "description": "Bollinger Band mean reversion",
        "status": "active",
        "performance": {
          "signals_generated": 8,
          "avg_confidence": 0.65,
          "success_rate": 0.62
        }
      }
    ],
    "total_strategies": 5,
    "active_strategies": 5
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### GET /strategies/{strategy_name}

Get detailed information about a specific strategy.

**Response:**
```json
{
  "status": "success",
  "data": {
    "name": "momentum_pulse",
    "description": "MACD histogram crossovers for momentum trading",
    "status": "active",
    "configuration": {
      "macd_fast": 12,
      "macd_slow": 26,
      "macd_signal": 9,
      "min_confidence": 0.6
    },
    "performance": {
      "signals_generated": 15,
      "avg_confidence": 0.72,
      "success_rate": 0.68,
      "last_signal": "2024-01-15T10:30:00Z"
    },
    "indicators": ["macd", "rsi", "adx"]
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## ⚙️ Configuration Endpoints

### GET /config

Get current configuration.

**Response:**
```json
{
  "status": "success",
  "data": {
    "environment": "production",
    "nats_url": "nats://nats-server:4222",
    "api_endpoint": "http://api-server:8080/signals",
    "supported_symbols": ["BTCUSDT", "ETHUSDT", "ADAUSDT"],
    "supported_timeframes": ["15m", "1h"],
    "indicators": {
      "rsi_period": 14,
      "macd_fast": 12,
      "macd_slow": 26,
      "macd_signal": 9,
      "adx_period": 14,
      "bb_period": 20,
      "bb_std": 2.0,
      "atr_period": 14
    },
    "confidence": {
      "min_confidence": 0.6,
      "weights": {
        "rsi": 0.2,
        "macd": 0.3,
        "adx": 0.2,
        "bb": 0.2,
        "atr": 0.1
      }
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 📝 Signal Format

### Signal Object

```json
{
  "symbol": "BTCUSDT",
  "period": "15m",
  "signal": "BUY|SELL",
  "confidence": 0.74,
  "strategy": "momentum_pulse",
  "metadata": {
    "rsi": 58.3,
    "macd_hist": 0.0012,
    "adx": 27,
    "bollinger_position": 0.6,
    "atr": 150.0
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | string | Trading symbol (e.g., "BTCUSDT") |
| `period` | string | Timeframe (e.g., "15m", "1h") |
| `signal` | string | Signal direction ("BUY" or "SELL") |
| `confidence` | float | Confidence score (0.0 to 1.0) |
| `strategy` | string | Strategy that generated the signal |
| `metadata` | object | Technical indicators and analysis data |
| `timestamp` | string | ISO 8601 timestamp |

### Metadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `rsi` | float | Relative Strength Index (0-100) |
| `macd_hist` | float | MACD histogram value |
| `adx` | float | Average Directional Index (0-100) |
| `bollinger_position` | float | Position within Bollinger Bands (0-1) |
| `atr` | float | Average True Range |

## 🚨 Error Responses

### Standard Error Format

```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid symbol format",
    "details": {
      "field": "symbol",
      "value": "INVALID",
      "expected": "Valid trading symbol (e.g., BTCUSDT)"
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid request parameters |
| `NOT_FOUND` | 404 | Resource not found |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |
| `INTERNAL_ERROR` | 500 | Internal server error |

### Common Error Responses

#### Invalid Symbol
```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid symbol format",
    "details": {
      "field": "symbol",
      "value": "INVALID",
      "expected": "Valid trading symbol (e.g., BTCUSDT)"
    }
  }
}
```

#### Service Unavailable
```json
{
  "status": "error",
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "NATS connection failed",
    "details": {
      "component": "nats_listener",
      "retry_after": 30
    }
  }
}
```

## 🔧 Rate Limiting

The API implements rate limiting to prevent abuse:

- **Health endpoints**: 100 requests/minute
- **Signal endpoints**: 50 requests/minute
- **Metrics endpoints**: 10 requests/minute

Rate limit headers:
```
X-RateLimit-Limit: 50
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1640995260
```

## 📊 Monitoring

### Health Check Integration

The API integrates with Kubernetes health checks:

```yaml
livenessProbe:
  httpGet:
    path: /live
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Metrics Integration

Prometheus metrics are available at `/metrics` for monitoring:

- Signal generation rate
- Processing time distribution
- Strategy performance
- Error rates

## 🔒 Security

### Internal Access Only

The API is designed for internal use within the Kubernetes cluster:

- No external authentication required
- Network policies restrict access
- TLS termination at ingress level

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ta-bot-network-policy
  namespace: petrosa-apps
spec:
  podSelector:
    matchLabels:
      app: petrosa-ta-bot
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
```

## 📚 SDK Examples

### Python Client

```python
import requests
import json

class TASignalClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def get_health(self):
        """Get service health status."""
        response = requests.get(f"{self.base_url}/health")
        return response.json()
    
    def generate_signals(self, candle_data: dict):
        """Generate trading signals."""
        response = requests.post(
            f"{self.base_url}/signals",
            json=candle_data
        )
        return response.json()
    
    def get_signals(self, symbol: str, limit: int = 10):
        """Get recent signals for a symbol."""
        params = {"limit": limit}
        response = requests.get(
            f"{self.base_url}/signals/{symbol}",
            params=params
        )
        return response.json()

# Usage
client = TASignalClient()
health = client.get_health()
print(f"Service status: {health['status']}")
```

### JavaScript Client

```javascript
class TASignalClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }
    
    async getHealth() {
        const response = await fetch(`${this.baseUrl}/health`);
        return response.json();
    }
    
    async generateSignals(candleData) {
        const response = await fetch(`${this.baseUrl}/signals`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(candleData)
        });
        return response.json();
    }
    
    async getSignals(symbol, limit = 10) {
        const params = new URLSearchParams({ limit });
        const response = await fetch(`${this.baseUrl}/signals/${symbol}?${params}`);
        return response.json();
    }
}

// Usage
const client = new TASignalClient();
const health = await client.getHealth();
console.log(`Service status: ${health.status}`);
```

## 📋 API Versioning

Current API version: **v1**

Version information is included in response headers:
```
X-API-Version: v1
X-API-Deprecated: false
```

## 🔗 Related Documentation

- **Signal Engine**: See [Signal Engine](./SIGNAL_ENGINE.md) for core analysis details
- **Trading Strategies**: Review [Strategies](./STRATEGIES.md) for strategy information
- **Configuration**: Check [Configuration](./CONFIGURATION.md) for environment setup
- **Deployment**: Read [Deployment Guide](./DEPLOYMENT.md) for production setup

---

**Next Steps**:
- Review [Signal Engine](./SIGNAL_ENGINE.md) for core analysis details
- Check [Trading Strategies](./STRATEGIES.md) for strategy information
- See [Configuration](./CONFIGURATION.md) for environment setup 