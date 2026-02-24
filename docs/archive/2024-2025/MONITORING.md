# Monitoring Guide

Comprehensive monitoring and observability guide for the Petrosa TA Bot.

## 📊 Monitoring Overview

### Monitoring Stack

```
┌─────────────────────────────────────────────────────────────┐
│                    Monitoring Stack                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │  Prometheus │  │   Grafana   │  │   Alert     │       │
│  │  (Metrics)  │  │  (Dashboards)│  │  Manager    │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
│           │               │               │               │
│           └───────────────┼───────────────┘               │
│                           │                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              TA Bot Application                    │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │   │
│  │  │   Health    │  │   Metrics   │  │   Logging   │ │   │
│  │  │   Checks    │  │  (Prometheus)│  │  (Structured)│ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘ │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Key Metrics

- **Application Metrics**: Signal generation rate, processing time
- **Infrastructure Metrics**: CPU, memory, network usage
- **Business Metrics**: Trading signal accuracy, strategy performance
- **Error Metrics**: Error rates, failure patterns

## 🏥 Health Checks

### Health Endpoints

The TA Bot provides three health check endpoints:

#### 1. Liveness Probe (`/live`)

```bash
# Check if application is alive
curl http://localhost:8000/live
```

**Response:**
```json
{
  "status": "alive",
  "uptime": "2h 30m 15s",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### 2. Readiness Probe (`/ready`)

```bash
# Check if application is ready to receive traffic
curl http://localhost:8000/ready
```

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

#### 3. Health Check (`/health`)

```bash
# Get detailed health status
curl http://localhost:8000/health
```

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

### Kubernetes Health Checks

```yaml
# deployment.yaml
livenessProbe:
  httpGet:
    path: /live
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3

startupProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 30
```

## 📈 Metrics Collection

### Prometheus Metrics

The TA Bot exposes Prometheus-compatible metrics at `/metrics`:

```bash
# Get metrics
curl http://localhost:8000/metrics
```

#### Application Metrics

```
# Signal generation metrics
ta_bot_signals_generated_total{strategy="momentum_pulse"} 15
ta_bot_signals_generated_total{strategy="band_fade_reversal"} 8

# Signal confidence distribution
ta_bot_signal_confidence_bucket{strategy="momentum_pulse",le="0.1"} 0
ta_bot_signal_confidence_bucket{strategy="momentum_pulse",le="0.5"} 2
ta_bot_signal_confidence_bucket{strategy="momentum_pulse",le="0.9"} 12
ta_bot_signal_confidence_bucket{strategy="momentum_pulse",le="+Inf"} 15

# Processing time metrics
ta_bot_processing_time_seconds_bucket{le="0.01"} 5
ta_bot_processing_time_seconds_bucket{le="0.05"} 15
ta_bot_processing_time_seconds_bucket{le="0.1"} 20
ta_bot_processing_time_seconds_bucket{le="+Inf"} 25

# Error metrics
ta_bot_errors_total{type="nats_connection"} 2
ta_bot_errors_total{type="api_publish"} 1

# Component status
ta_bot_component_status{component="signal_engine"} 1
ta_bot_component_status{component="nats_listener"} 1
ta_bot_component_status{component="publisher"} 1
```

#### Infrastructure Metrics

```
# Resource usage
container_cpu_usage_seconds_total{container="ta-bot"}
container_memory_usage_bytes{container="ta-bot"}

# Network metrics
container_network_receive_bytes_total{container="ta-bot"}
container_network_transmit_bytes_total{container="ta-bot"}

# Pod status
kube_pod_status_phase{namespace="petrosa-apps",pod=~"petrosa-ta-bot.*"}
```

### Metrics Implementation

```python
# ta_bot/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from typing import Dict, Any

# Metrics
SIGNALS_GENERATED = Counter(
    'ta_bot_signals_generated_total',
    'Total signals generated',
    ['strategy']
)

SIGNAL_CONFIDENCE = Histogram(
    'ta_bot_signal_confidence',
    'Signal confidence distribution',
    ['strategy'],
    buckets=[0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
)

PROCESSING_TIME = Histogram(
    'ta_bot_processing_time_seconds',
    'Signal processing time',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0]
)

ERRORS_TOTAL = Counter(
    'ta_bot_errors_total',
    'Total errors',
    ['type']
)

COMPONENT_STATUS = Gauge(
    'ta_bot_component_status',
    'Component status (1=healthy, 0=unhealthy)',
    ['component']
)

def record_signal(strategy: str, confidence: float):
    """Record signal generation."""
    SIGNALS_GENERATED.labels(strategy=strategy).inc()
    SIGNAL_CONFIDENCE.labels(strategy=strategy).observe(confidence)

def record_processing_time(duration: float):
    """Record processing time."""
    PROCESSING_TIME.observe(duration)

def record_error(error_type: str):
    """Record error occurrence."""
    ERRORS_TOTAL.labels(type=error_type).inc()

def update_component_status(component: str, healthy: bool):
    """Update component status."""
    status = 1 if healthy else 0
    COMPONENT_STATUS.labels(component=component).set(status)

def get_metrics() -> str:
    """Get Prometheus metrics."""
    return generate_latest()
```

## 📊 Dashboards

### Grafana Dashboard

Create a Grafana dashboard with the following panels:

#### 1. Signal Generation Overview

```json
{
  "title": "Signal Generation Overview",
  "panels": [
    {
      "title": "Signals Generated per Strategy",
      "type": "graph",
      "targets": [
        {
          "expr": "rate(ta_bot_signals_generated_total[5m])",
          "legendFormat": "{{strategy}}"
        }
      ]
    },
    {
      "title": "Signal Confidence Distribution",
      "type": "heatmap",
      "targets": [
        {
          "expr": "rate(ta_bot_signal_confidence_bucket[5m])",
          "legendFormat": "{{le}}"
        }
      ]
    }
  ]
}
```

#### 2. Performance Metrics

```json
{
  "title": "Performance Metrics",
  "panels": [
    {
      "title": "Processing Time",
      "type": "graph",
      "targets": [
        {
          "expr": "histogram_quantile(0.95, rate(ta_bot_processing_time_seconds_bucket[5m]))",
          "legendFormat": "95th percentile"
        },
        {
          "expr": "histogram_quantile(0.50, rate(ta_bot_processing_time_seconds_bucket[5m]))",
          "legendFormat": "50th percentile"
        }
      ]
    },
    {
      "title": "Error Rate",
      "type": "graph",
      "targets": [
        {
          "expr": "rate(ta_bot_errors_total[5m])",
          "legendFormat": "{{type}}"
        }
      ]
    }
  ]
}
```

#### 3. Infrastructure Metrics

```json
{
  "title": "Infrastructure Metrics",
  "panels": [
    {
      "title": "CPU Usage",
      "type": "graph",
      "targets": [
        {
          "expr": "rate(container_cpu_usage_seconds_total{container=\"ta-bot\"}[5m]) * 100",
          "legendFormat": "CPU %"
        }
      ]
    },
    {
      "title": "Memory Usage",
      "type": "graph",
      "targets": [
        {
          "expr": "container_memory_usage_bytes{container=\"ta-bot\"} / 1024 / 1024",
          "legendFormat": "Memory MB"
        }
      ]
    }
  ]
}
```

## 🚨 Alerting Rules

### Prometheus Alert Rules

```yaml
# alerts/ta-bot-alerts.yaml
groups:
- name: ta-bot-alerts
  rules:
  # Pod health alerts
  - alert: TAPodDown
    expr: up{job="petrosa-ta-bot"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "TA Bot pod is down"
      description: "Pod {{ $labels.pod }} is not responding"

  - alert: TAHighErrorRate
    expr: rate(ta_bot_errors_total[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High error rate in TA Bot"
      description: "Error rate is {{ $value }} errors/second"

  # Signal generation alerts
  - alert: TANoSignals
    expr: rate(ta_bot_signals_generated_total[10m]) == 0
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "No signals generated in 10 minutes"
      description: "No trading signals have been generated"

  - alert: TALowConfidenceSignals
    expr: histogram_quantile(0.5, rate(ta_bot_signal_confidence_bucket[5m])) < 0.6
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "Low confidence signals"
      description: "Median signal confidence is {{ $value }}"

  # Performance alerts
  - alert: TAHighProcessingTime
    expr: histogram_quantile(0.95, rate(ta_bot_processing_time_seconds_bucket[5m])) > 0.1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High processing time"
      description: "95th percentile processing time is {{ $value }}s"

  # Infrastructure alerts
  - alert: TAHighCPUUsage
    expr: rate(container_cpu_usage_seconds_total{container="ta-bot"}[5m]) * 100 > 80
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High CPU usage"
      description: "CPU usage is {{ $value }}%"

  - alert: TAHighMemoryUsage
    expr: (container_memory_usage_bytes{container="ta-bot"} / container_spec_memory_limit_bytes{container="ta-bot"}) * 100 > 80
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage"
      description: "Memory usage is {{ $value }}%"

  # Component health alerts
  - alert: TAComponentUnhealthy
    expr: ta_bot_component_status == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "TA Bot component unhealthy"
      description: "Component {{ $labels.component }} is unhealthy"
```

### Alert Manager Configuration

```yaml
# alertmanager/config.yaml
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'ta-bot@petrosa.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'team-petrosa'

receivers:
- name: 'team-petrosa'
  email_configs:
  - to: 'team@petrosa.com'
    send_resolved: true
  slack_configs:
  - api_url: 'https://hooks.slack.com/services/...'
    channel: '#alerts'
    send_resolved: true
```

## 📝 Logging

### Structured Logging

```python
# ta_bot/logging.py
import structlog
import logging
from typing import Dict, Any

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

def log_signal_generation(signal: Dict[str, Any]):
    """Log signal generation."""
    logger.info(
        "Signal generated",
        symbol=signal['symbol'],
        strategy=signal['strategy'],
        confidence=signal['confidence'],
        signal_type=signal['signal']
    )

def log_error(error_type: str, error_message: str, **kwargs):
    """Log error with context."""
    logger.error(
        "Error occurred",
        error_type=error_type,
        error_message=error_message,
        **kwargs
    )

def log_performance(operation: str, duration: float, **kwargs):
    """Log performance metrics."""
    logger.info(
        "Performance metric",
        operation=operation,
        duration=duration,
        **kwargs
    )
```

### Log Format

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "info",
  "logger": "ta_bot.signal_engine",
  "event": "Signal generated",
  "symbol": "BTCUSDT",
  "strategy": "momentum_pulse",
  "confidence": 0.74,
  "signal_type": "BUY",
  "processing_time": 0.045
}
```

### Log Aggregation

```yaml
# fluentd-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
  namespace: petrosa-apps
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/containers/petrosa-ta-bot-*.log
      pos_file /var/log/fluentd-containers.log.pos
      tag kubernetes.*
      read_from_head true
      <parse>
        @type json
        time_key time
        time_format %Y-%m-%dT%H:%M:%S.%NZ
      </parse>
    </source>

    <filter kubernetes.**>
      @type kubernetes_metadata
    </filter>

    <match kubernetes.**>
      @type elasticsearch
      host elasticsearch-master
      port 9200
      logstash_format true
      logstash_prefix k8s
    </match>
```

## 🔍 Tracing

### Distributed Tracing

```python
# ta_bot/tracing.py
import opentracing
from jaeger_client import Config
from typing import Optional

def init_tracer(service_name: str = "ta-bot"):
    """Initialize Jaeger tracer."""
    config = Config(
        config={
            'sampler': {
                'type': 'const',
                'param': True,
            },
            'logging': True,
        },
        service_name=service_name,
    )
    return config.initialize_tracer()

def trace_signal_generation(func):
    """Decorator to trace signal generation."""
    def wrapper(*args, **kwargs):
        tracer = opentracing.global_tracer()
        with tracer.start_span("signal_generation") as span:
            span.set_tag("component", "signal_engine")
            result = func(*args, **kwargs)
            if result:
                span.set_tag("signal_generated", True)
                span.set_tag("strategy", result.strategy)
                span.set_tag("confidence", result.confidence)
            return result
    return wrapper
```

## 📊 Business Metrics

### Trading Performance Metrics

```python
# ta_bot/business_metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Business metrics
SIGNAL_ACCURACY = Histogram(
    'ta_bot_signal_accuracy',
    'Signal accuracy by strategy',
    ['strategy'],
    buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

PROFIT_LOSS = Counter(
    'ta_bot_profit_loss_total',
    'Total profit/loss by strategy',
    ['strategy']
)

WIN_RATE = Gauge(
    'ta_bot_win_rate',
    'Win rate by strategy',
    ['strategy']
)

def record_signal_accuracy(strategy: str, accuracy: float):
    """Record signal accuracy."""
    SIGNAL_ACCURACY.labels(strategy=strategy).observe(accuracy)

def record_profit_loss(strategy: str, pnl: float):
    """Record profit/loss."""
    PROFIT_LOSS.labels(strategy=strategy).inc(pnl)

def update_win_rate(strategy: str, win_rate: float):
    """Update win rate."""
    WIN_RATE.labels(strategy=strategy).set(win_rate)
```

## 🚀 Monitoring Setup

### Prometheus Configuration

```yaml
# prometheus-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s

    rule_files:
      - /etc/prometheus/rules/*.yaml

    scrape_configs:
      - job_name: 'ta-bot'
        static_configs:
          - targets: ['petrosa-ta-bot-service.petrosa-apps.svc.cluster.local:80']
        metrics_path: '/metrics'
        scrape_interval: 10s

      - job_name: 'kubernetes-pods'
        kubernetes_sd_configs:
          - role: pod
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
            action: keep
            regex: true
          - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
            action: replace
            target_label: __metrics_path__
            regex: (.+)
          - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
            action: replace
            regex: ([^:]+)(?::\d+)?;(\d+)
            replacement: $1:$2
            target_label: __address__
```

### Grafana Configuration

```yaml
# grafana-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboards
  namespace: monitoring
data:
  ta-bot-dashboard.json: |
    {
      "dashboard": {
        "title": "TA Bot Dashboard",
        "panels": [
          // Dashboard panels configuration
        ]
      }
    }
```

## 📋 Monitoring Checklist

### Setup Checklist

- [ ] **Prometheus**: Installed and configured
- [ ] **Grafana**: Installed with dashboards
- [ ] **Alert Manager**: Configured with rules
- [ ] **Log Aggregation**: Fluentd/ELK stack setup
- [ ] **Tracing**: Jaeger or similar configured
- [ ] **Metrics**: Application metrics exposed
- [ ] **Health Checks**: Kubernetes probes configured
- [ ] **Alerts**: Alert rules defined and tested

### Operational Checklist

- [ ] **Dashboard Access**: Team has access to dashboards
- [ ] **Alert Notifications**: Alerts configured for team
- [ ] **Log Access**: Logs accessible for debugging
- [ ] **Metrics Retention**: Appropriate retention policies
- [ ] **Performance Baselines**: Performance baselines established
- [ ] **Incident Response**: Runbooks for common issues

## 🔗 Related Documentation

- **Deployment Guide**: See [Deployment Guide](./DEPLOYMENT.md) for deployment details
- **Kubernetes Configuration**: Check [Kubernetes Configuration](./KUBERNETES.md) for K8s setup
- **Troubleshooting**: Review [Troubleshooting](./TROUBLESHOOTING.md) for common issues
- **Configuration**: Read [Configuration](./CONFIGURATION.md) for environment setup

---

**Next Steps**:
- Read [Deployment Guide](./DEPLOYMENT.md) for deployment details
- Check [Kubernetes Configuration](./KUBERNETES.md) for K8s setup
- Review [Troubleshooting](./TROUBLESHOOTING.md) for common issues
