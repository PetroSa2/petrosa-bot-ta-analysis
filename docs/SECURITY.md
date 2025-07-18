# Security Guide

Comprehensive security guide for the Petrosa TA Bot.

## 🔒 Security Overview

### Security Principles

- **Defense in Depth**: Multiple layers of security controls
- **Least Privilege**: Minimal permissions required for operation
- **Zero Trust**: Verify everything, trust nothing
- **Security by Design**: Security built into the architecture
- **Continuous Monitoring**: Ongoing security monitoring and alerting

### Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Security Layers                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │   Network   │  │   Container │  │ Application │       │
│  │   Security  │  │   Security  │  │   Security  │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
│           │               │               │               │
│           └───────────────┼───────────────┘               │
│                           │                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Infrastructure Security                │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │   │
│  │  │   Secrets   │  │   RBAC      │  │   Network   │ │   │
│  │  │ Management  │  │   Control   │  │   Policies  │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘ │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 🛡️ Application Security

### Input Validation

```python
# ta_bot/security/validation.py
from pydantic import BaseModel, validator, Field
from typing import List, Optional
import re

class CandleDataValidator(BaseModel):
    """Validate candle data input."""
    
    symbol: str = Field(..., min_length=1, max_length=20)
    period: str = Field(..., regex=r'^(1m|5m|15m|1h|4h|1d)$')
    timestamp: int = Field(..., gt=0)
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    volume: float = Field(..., ge=0)
    
    @validator('symbol')
    def validate_symbol(cls, v):
        """Validate trading symbol format."""
        if not re.match(r'^[A-Z0-9]+$', v):
            raise ValueError('Symbol must contain only uppercase letters and numbers')
        return v
    
    @validator('high')
    def validate_high(cls, v, values):
        """Validate high price is highest."""
        if 'low' in values and v < values['low']:
            raise ValueError('High price must be greater than low price')
        return v
    
    @validator('low')
    def validate_low(cls, v, values):
        """Validate low price is lowest."""
        if 'high' in values and v > values['high']:
            raise ValueError('Low price must be less than high price')
        return v

class SignalValidator(BaseModel):
    """Validate signal output."""
    
    symbol: str = Field(..., min_length=1, max_length=20)
    period: str = Field(..., regex=r'^(1m|5m|15m|1h|4h|1d)$')
    signal: str = Field(..., regex=r'^(BUY|SELL)$')
    confidence: float = Field(..., ge=0.0, le=1.0)
    strategy: str = Field(..., min_length=1, max_length=50)
    metadata: dict = Field(default_factory=dict)
    
    @validator('strategy')
    def validate_strategy(cls, v):
        """Validate strategy name."""
        allowed_strategies = [
            'momentum_pulse',
            'band_fade_reversal',
            'golden_trend_sync',
            'range_break_pop',
            'divergence_trap'
        ]
        if v not in allowed_strategies:
            raise ValueError(f'Strategy must be one of {allowed_strategies}')
        return v
```

### Authentication & Authorization

```python
# ta_bot/security/auth.py
import jwt
import hashlib
import hmac
import time
from typing import Optional, Dict, Any
from functools import wraps

class SecurityManager:
    """Security manager for authentication and authorization."""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
    
    def generate_token(self, user_id: str, expires_in: int = 3600) -> str:
        """Generate JWT token."""
        payload = {
            'user_id': user_id,
            'exp': time.time() + expires_in,
            'iat': time.time()
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def verify_hmac(self, data: str, signature: str, secret: str) -> bool:
        """Verify HMAC signature."""
        expected_signature = hmac.new(
            secret.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected_signature)

def require_auth(func):
    """Decorator to require authentication."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Authentication logic here
        return func(*args, **kwargs)
    return wrapper

def require_role(role: str):
    """Decorator to require specific role."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Role-based authorization logic here
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

### Secure Configuration

```python
# ta_bot/security/config.py
import os
from typing import Optional
from pydantic import BaseSettings, Field

class SecurityConfig(BaseSettings):
    """Security configuration."""
    
    # JWT settings
    jwt_secret_key: str = Field(..., env='JWT_SECRET_KEY')
    jwt_algorithm: str = Field(default='HS256', env='JWT_ALGORITHM')
    jwt_expires_in: int = Field(default=3600, env='JWT_EXPIRES_IN')
    
    # API security
    api_rate_limit: int = Field(default=100, env='API_RATE_LIMIT')
    api_rate_limit_window: int = Field(default=60, env='API_RATE_LIMIT_WINDOW')
    
    # CORS settings
    cors_origins: list = Field(default=['*'], env='CORS_ORIGINS')
    cors_methods: list = Field(default=['GET', 'POST'], env='CORS_METHODS')
    
    # TLS settings
    tls_cert_file: Optional[str] = Field(None, env='TLS_CERT_FILE')
    tls_key_file: Optional[str] = Field(None, env='TLS_KEY_FILE')
    
    # Security headers
    security_headers: dict = Field(default={
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
    })
    
    class Config:
        env_prefix = 'SECURITY_'
```

### Rate Limiting

```python
# ta_bot/security/rate_limit.py
import time
import threading
from typing import Dict, Tuple
from collections import defaultdict

class RateLimiter:
    """Rate limiter implementation."""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
        self.lock = threading.Lock()
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed."""
        now = time.time()
        
        with self.lock:
            # Clean old requests
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id]
                if now - req_time < self.window_seconds
            ]
            
            # Check if under limit
            if len(self.requests[client_id]) < self.max_requests:
                self.requests[client_id].append(now)
                return True
            
            return False
    
    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests for client."""
        now = time.time()
        
        with self.lock:
            valid_requests = [
                req_time for req_time in self.requests[client_id]
                if now - req_time < self.window_seconds
            ]
            
            return max(0, self.max_requests - len(valid_requests))

# Global rate limiter
rate_limiter = RateLimiter(max_requests=100, window_seconds=60)

def rate_limit(func):
    """Decorator to apply rate limiting."""
    def wrapper(*args, **kwargs):
        client_id = get_client_id()  # Extract client ID from request
        if not rate_limiter.is_allowed(client_id):
            raise RateLimitExceeded("Rate limit exceeded")
        return func(*args, **kwargs)
    return wrapper
```

## 🔐 Secrets Management

### Kubernetes Secrets

```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: ta-bot-secrets
  namespace: petrosa-apps
  labels:
    app: petrosa-ta-bot
type: Opaque
data:
  # Base64 encoded secrets
  # echo -n "your-secret-value" | base64
  nats_username: ""  # Replace with actual value
  nats_password: ""  # Replace with actual value
  api_auth_token: "" # Replace with actual value
  jwt_secret_key: "" # Replace with actual value
```

### Secrets Management Commands

```bash
# Create secrets
kubectl create secret generic ta-bot-secrets \
  --from-literal=nats-username="your-username" \
  --from-literal=nats-password="your-password" \
  --from-literal=api-auth-token="your-token" \
  --from-literal=jwt-secret-key="your-jwt-secret" \
  -n petrosa-apps

# Update secrets
kubectl apply -f k8s/secrets.yaml

# View secrets (base64 encoded)
kubectl get secret ta-bot-secrets -n petrosa-apps -o yaml

# Decode secret value
echo "base64-encoded-value" | base64 --decode
```

### Environment Variables Security

```python
# ta_bot/security/env.py
import os
from typing import Optional

class SecureEnvironment:
    """Secure environment variable management."""
    
    @staticmethod
    def get_secret(key: str, default: Optional[str] = None) -> str:
        """Get secret from environment variable."""
        value = os.getenv(key, default)
        if not value:
            raise ValueError(f"Required environment variable {key} not set")
        return value
    
    @staticmethod
    def get_optional_secret(key: str) -> Optional[str]:
        """Get optional secret from environment variable."""
        return os.getenv(key)
    
    @staticmethod
    def validate_required_secrets():
        """Validate all required secrets are present."""
        required_secrets = [
            'NATS_URL',
            'TA_BOT_API_ENDPOINT',
            'JWT_SECRET_KEY'
        ]
        
        missing_secrets = []
        for secret in required_secrets:
            if not os.getenv(secret):
                missing_secrets.append(secret)
        
        if missing_secrets:
            raise ValueError(f"Missing required secrets: {missing_secrets}")
```

## 🛡️ Container Security

### Dockerfile Security

```dockerfile
# Dockerfile with security best practices
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r ta-bot && useradd -r -g ta-bot ta-bot

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt requirements-dev.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r requirements-dev.txt

# Copy application code
COPY ta_bot/ ./ta_bot/
COPY scripts/ ./scripts/

# Set ownership to non-root user
RUN chown -R ta-bot:ta-bot /app

# Switch to non-root user
USER ta-bot

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["python", "-m", "ta_bot.main"]
```

### Container Security Scanning

```bash
# Scan container for vulnerabilities
trivy image yurisa2/petrosa-ta-bot:latest

# Scan with specific severity levels
trivy image --severity HIGH,CRITICAL yurisa2/petrosa-ta-bot:latest

# Generate security report
trivy image --format json --output security-report.json yurisa2/petrosa-ta-bot:latest
```

### Pod Security Standards

```yaml
# k8s/deployment-secure.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: petrosa-ta-bot
  namespace: petrosa-apps
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
      containers:
      - name: ta-bot
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
          seccompProfile:
            type: RuntimeDefault
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: varlog
          mountPath: /var/log
        - name: config
          mountPath: /app/config
          readOnly: true
      volumes:
      - name: tmp
        emptyDir: {}
      - name: varlog
        emptyDir: {}
      - name: config
        configMap:
          name: ta-bot-config
```

## 🌐 Network Security

### Network Policies

```yaml
# k8s/network-policy.yaml
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
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: nats-system
    ports:
    - protocol: TCP
      port: 4222
  - to:
    - namespaceSelector:
        matchLabels:
          name: api-system
    ports:
    - protocol: TCP
      port: 8080
  - to:
    - namespaceSelector:
        matchLabels:
          name: monitoring
    ports:
    - protocol: TCP
      port: 9090
```

### TLS Configuration

```yaml
# k8s/tls-certificate.yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: ta-bot-tls
  namespace: petrosa-apps
spec:
  secretName: ta-bot-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - ta-bot.petrosa.com
```

## 🔐 RBAC Configuration

### Service Account

```yaml
# k8s/service-account.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ta-bot-service-account
  namespace: petrosa-apps
  labels:
    app: petrosa-ta-bot
```

### Role

```yaml
# k8s/role.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: petrosa-apps
  name: ta-bot-role
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get"]
  resourceNames: ["ta-bot-config", "ta-bot-secrets"]
```

### Role Binding

```yaml
# k8s/role-binding.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: ta-bot-role-binding
  namespace: petrosa-apps
subjects:
- kind: ServiceAccount
  name: ta-bot-service-account
  namespace: petrosa-apps
roleRef:
  kind: Role
  name: ta-bot-role
  apiGroup: rbac.authorization.k8s.io
```

## 🔍 Security Monitoring

### Security Logging

```python
# ta_bot/security/logging.py
import logging
import structlog
from typing import Dict, Any

logger = structlog.get_logger()

def log_security_event(event_type: str, details: Dict[str, Any]):
    """Log security events."""
    logger.warning(
        "Security event",
        event_type=event_type,
        details=details,
        severity="security"
    )

def log_authentication_attempt(user_id: str, success: bool, ip_address: str):
    """Log authentication attempts."""
    logger.info(
        "Authentication attempt",
        user_id=user_id,
        success=success,
        ip_address=ip_address,
        severity="security"
    )

def log_authorization_failure(user_id: str, resource: str, action: str):
    """Log authorization failures."""
    logger.warning(
        "Authorization failure",
        user_id=user_id,
        resource=resource,
        action=action,
        severity="security"
    )
```

### Security Metrics

```python
# ta_bot/security/metrics.py
from prometheus_client import Counter, Histogram

# Security metrics
SECURITY_EVENTS = Counter(
    'ta_bot_security_events_total',
    'Total security events',
    ['event_type', 'severity']
)

AUTHENTICATION_ATTEMPTS = Counter(
    'ta_bot_authentication_attempts_total',
    'Total authentication attempts',
    ['success']
)

AUTHORIZATION_FAILURES = Counter(
    'ta_bot_authorization_failures_total',
    'Total authorization failures',
    ['resource', 'action']
)

RATE_LIMIT_EXCEEDED = Counter(
    'ta_bot_rate_limit_exceeded_total',
    'Total rate limit violations',
    ['client_id']
)

def record_security_event(event_type: str, severity: str = "medium"):
    """Record security event."""
    SECURITY_EVENTS.labels(event_type=event_type, severity=severity).inc()

def record_auth_attempt(success: bool):
    """Record authentication attempt."""
    AUTHENTICATION_ATTEMPTS.labels(success=str(success).lower()).inc()

def record_auth_failure(resource: str, action: str):
    """Record authorization failure."""
    AUTHORIZATION_FAILURES.labels(resource=resource, action=action).inc()

def record_rate_limit_violation(client_id: str):
    """Record rate limit violation."""
    RATE_LIMIT_EXCEEDED.labels(client_id=client_id).inc()
```

## 🚨 Security Alerts

### Security Alert Rules

```yaml
# alerts/security-alerts.yaml
groups:
- name: security-alerts
  rules:
  - alert: SecurityEventDetected
    expr: rate(ta_bot_security_events_total[5m]) > 0
    for: 1m
    labels:
      severity: warning
    annotations:
      summary: "Security event detected"
      description: "{{ $value }} security events per second"
  
  - alert: HighAuthFailures
    expr: rate(ta_bot_authentication_attempts_total{success="false"}[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High authentication failure rate"
      description: "{{ $value }} failed auth attempts per second"
  
  - alert: AuthorizationFailures
    expr: rate(ta_bot_authorization_failures_total[5m]) > 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Authorization failures detected"
      description: "{{ $value }} authorization failures per second"
  
  - alert: RateLimitViolations
    expr: rate(ta_bot_rate_limit_exceeded_total[5m]) > 0.5
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High rate limit violations"
      description: "{{ $value }} rate limit violations per second"
```

## 📋 Security Checklist

### Development Security

- [ ] **Input Validation**: All inputs validated and sanitized
- [ ] **Authentication**: Proper authentication implemented
- [ ] **Authorization**: Role-based access control
- [ ] **Secrets**: No hardcoded secrets in code
- [ ] **Dependencies**: Regular security updates
- [ ] **Code Review**: Security-focused code reviews
- [ ] **Testing**: Security testing included

### Deployment Security

- [ ] **Container Security**: Non-root user, read-only filesystem
- [ ] **Network Policies**: Proper network isolation
- [ ] **RBAC**: Minimal required permissions
- [ ] **Secrets Management**: Secure secrets handling
- [ ] **TLS**: HTTPS with valid certificates
- [ ] **Monitoring**: Security event monitoring
- [ ] **Updates**: Regular security patches

### Operational Security

- [ ] **Access Control**: Limited access to production
- [ ] **Monitoring**: Security event monitoring
- [ ] **Incident Response**: Security incident procedures
- [ ] **Backup Security**: Encrypted backups
- [ ] **Logging**: Comprehensive security logging
- [ ] **Audit**: Regular security audits
- [ ] **Training**: Security awareness training

## 🔗 Related Documentation

- **Deployment Guide**: See [Deployment Guide](./DEPLOYMENT.md) for secure deployment
- **Kubernetes Configuration**: Check [Kubernetes Configuration](./KUBERNETES.md) for K8s security
- **Monitoring Guide**: Review [Monitoring Guide](./MONITORING.md) for security monitoring
- **Configuration**: Read [Configuration](./CONFIGURATION.md) for security settings

---

**Next Steps**:
- Read [Deployment Guide](./DEPLOYMENT.md) for secure deployment
- Check [Kubernetes Configuration](./KUBERNETES.md) for K8s security
- Review [Monitoring Guide](./MONITORING.md) for security monitoring 