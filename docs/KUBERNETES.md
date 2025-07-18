# Kubernetes Configuration

Complete Kubernetes setup and configuration for the Petrosa TA Bot.

## 🏗️ Architecture Overview

### Cluster Setup

The TA Bot runs on a **remote MicroK8s cluster** with the following components:

```
┌─────────────────────────────────────────────────────────────┐
│                    Remote MicroK8s Cluster                 │
├─────────────────────────────────────────────────────────────┤
│  Namespace: petrosa-apps                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   Ingress       │  │   Service       │  │   HPA       │ │
│  │   (Nginx)       │  │   (ClusterIP)   │  │   (Auto)    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
│           │                     │                    │      │
│           └─────────────────────┼────────────────────┘      │
│                                 │                           │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Deployment (3 replicas)                   │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │ │
│  │  │   Pod 1     │  │   Pod 2     │  │   Pod 3     │   │ │
│  │  │   TA Bot    │  │   TA Bot    │  │   TA Bot    │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘   │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   ConfigMap     │  │   Secrets       │  │   Network   │ │
│  │   (Config)      │  │   (Auth)        │  │   Policy    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Manifests Structure

```
k8s/
├── deployment.yaml      # Main application deployment
├── service.yaml         # Network service
├── ingress.yaml         # External access
├── hpa.yaml            # Horizontal Pod Autoscaler
├── configmap.yaml      # Configuration
├── secrets.yaml        # Sensitive data
└── kubeconfig.yaml     # Cluster configuration
```

## 🚀 Deployment Components

### 1. Deployment (`k8s/deployment.yaml`)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: petrosa-ta-bot
  namespace: petrosa-apps
  labels:
    app: petrosa-ta-bot
    version: VERSION_PLACEHOLDER
spec:
  replicas: 3
  selector:
    matchLabels:
      app: petrosa-ta-bot
  template:
    metadata:
      labels:
        app: petrosa-ta-bot
        version: VERSION_PLACEHOLDER
    spec:
      containers:
      - name: ta-bot
        image: yurisa2/petrosa-ta-bot:VERSION_PLACEHOLDER
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: NATS_URL
          valueFrom:
            configMapKeyRef:
              name: petrosa-global-config
              key: NATS_URL
        - name: TA_BOT_API_ENDPOINT
          valueFrom:
            configMapKeyRef:
              name: petrosa-common-config
              key: TA_BOT_API_ENDPOINT
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
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
        startupProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
          failureThreshold: 30
```

### 2. Service (`k8s/service.yaml`)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: petrosa-ta-bot-service
  namespace: petrosa-apps
  labels:
    app: petrosa-ta-bot
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
    name: http
  selector:
    app: petrosa-ta-bot
```

### 3. Ingress (`k8s/ingress.yaml`)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: petrosa-ta-bot-ingress
  namespace: petrosa-apps
  labels:
    app: petrosa-ta-bot
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - ta-bot.petrosa.com
    secretName: ta-bot-tls
  rules:
  - host: ta-bot.petrosa.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: petrosa-ta-bot-service
            port:
              number: 80
```

### 4. HPA (`k8s/hpa.yaml`)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: petrosa-ta-bot-hpa
  namespace: petrosa-apps
  labels:
    app: petrosa-ta-bot
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: petrosa-ta-bot
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
```

### 5. ConfigMap (`k8s/configmap.yaml`)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ta-bot-config
  namespace: petrosa-apps
  labels:
    app: petrosa-ta-bot
data:
  nats_url: "nats://nats-server:4222"
  api_endpoint: "http://api-server:8080/signals"
  log_level: "INFO"
  environment: "production"
  supported_symbols: "BTCUSDT,ETHUSDT,ADAUSDT"
  supported_timeframes: "15m,1h"
  rsi_period: "14"
  macd_fast: "12"
  macd_slow: "26"
  macd_signal: "9"
  adx_period: "14"
  bb_period: "20"
  bb_std: "2.0"
  atr_period: "14"
```

### 6. Secrets (`k8s/secrets.yaml`)

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: ta-bot-secrets
  namespace: petrosa-apps
  labels:
    app: petrosa-ta-bot
type: Opaque
data:
  # Base64 encoded secrets - replace with actual values
  # echo -n "your-secret-value" | base64
  nats_username: ""
  nats_password: ""
  api_auth_token: ""
```

## 🔧 Configuration Management

### Environment Variables

The application uses environment variables for configuration:

```bash
# Core Configuration
NATS_URL=nats://nats-server:4222
TA_BOT_API_ENDPOINT=http://api-server:8080/signals
TA_BOT_LOG_LEVEL=INFO
TA_BOT_ENVIRONMENT=production

# Trading Configuration
TA_BOT_SUPPORTED_SYMBOLS=BTCUSDT,ETHUSDT,ADAUSDT
TA_BOT_SUPPORTED_TIMEFRAMES=15m,1h

# Technical Analysis Configuration
TA_BOT_RSI_PERIOD=14
TA_BOT_MACD_FAST=12
TA_BOT_MACD_SLOW=26
TA_BOT_MACD_SIGNAL=9
TA_BOT_ADX_PERIOD=14
TA_BOT_BB_PERIOD=20
TA_BOT_BB_STD=2.0
TA_BOT_ATR_PERIOD=14
```

### ConfigMap Management

```bash
# Create configmap from file
kubectl create configmap ta-bot-config \
  --from-file=k8s/configmap.yaml \
  -n petrosa-apps

# Update configmap
kubectl apply -f k8s/configmap.yaml

# View configmap
kubectl get configmap ta-bot-config -n petrosa-apps -o yaml
```

### Secrets Management

```bash
# Create secrets (replace with actual values)
kubectl create secret generic ta-bot-secrets \
  --from-literal=nats-username="your-username" \
  --from-literal=nats-password="your-password" \
  --from-literal=api-auth-token="your-token" \
  -n petrosa-apps

# Update secrets
kubectl apply -f k8s/secrets.yaml

# View secrets (base64 encoded)
kubectl get secret ta-bot-secrets -n petrosa-apps -o yaml
```

## 🚀 Deployment Commands

### Initial Setup

```bash
# Set kubeconfig for remote cluster
export KUBECONFIG=k8s/kubeconfig.yaml

# Create namespace
kubectl create namespace petrosa-apps

# Apply all manifests
kubectl apply -f k8s/
```

### Deployment Verification

```bash
# Check deployment status
kubectl get pods -n petrosa-apps -l app=petrosa-ta-bot

# Check service
kubectl get svc -n petrosa-apps -l app=petrosa-ta-bot

# Check ingress
kubectl get ingress -n petrosa-apps -l app=petrosa-ta-bot

# Check HPA
kubectl get hpa -n petrosa-apps petrosa-ta-bot-hpa
```

### Rolling Updates

```bash
# Update deployment
kubectl set image deployment/petrosa-ta-bot \
  ta-bot=yurisa2/petrosa-ta-bot:v1.1.0 \
  -n petrosa-apps

# Check rollout status
kubectl rollout status deployment/petrosa-ta-bot -n petrosa-apps

# Rollback if needed
kubectl rollout undo deployment/petrosa-ta-bot -n petrosa-apps
```

## 📊 Monitoring & Health Checks

### Health Endpoints

The application provides health check endpoints:

```yaml
# Liveness probe
livenessProbe:
  httpGet:
    path: /live
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

# Readiness probe
readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3

# Startup probe
startupProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 30
```

### Health Check Responses

```json
// GET /live
{
  "status": "alive",
  "uptime": "2h 30m 15s",
  "timestamp": "2024-01-15T10:30:00Z"
}

// GET /ready
{
  "status": "ready",
  "checks": {
    "nats_connection": "ok",
    "api_endpoint": "ok",
    "signal_engine": "ok"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}

// GET /health
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

## 🔒 Security Configuration

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
```

### RBAC Configuration

```yaml
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

---
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

### Pod Security Standards

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: ta-bot-pod
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 1000
  containers:
  - name: ta-bot
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    volumeMounts:
    - name: tmp
      mountPath: /tmp
    - name: varlog
      mountPath: /var/log
  volumes:
  - name: tmp
    emptyDir: {}
  - name: varlog
    emptyDir: {}
```

## 📈 Resource Management

### Resource Requests and Limits

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

### Horizontal Pod Autoscaling

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: petrosa-ta-bot-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: petrosa-ta-bot
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Vertical Pod Autoscaling (Optional)

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: ta-bot-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: petrosa-ta-bot
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: '*'
      minAllowed:
        cpu: 100m
        memory: 50Mi
      maxAllowed:
        cpu: 1
        memory: 500Mi
      controlledValues: RequestsAndLimits
```

## 🔄 CI/CD Integration

### GitHub Actions Deployment

The deployment is automated via GitHub Actions:

```yaml
# .github/workflows/ci.yml
deploy:
  name: Deploy to Kubernetes
  needs: [build-and-push, create-release]
  runs-on: ubuntu-latest
  environment: production
  steps:
  - name: Checkout code
    uses: actions/checkout@v4
  - name: Install kubectl
    uses: azure/setup-kubectl@v3
    with:
      version: 'v1.28.0'
  - name: Configure kubectl for MicroK8s
    run: |
      mkdir -p $HOME/.kube
      echo "${{ secrets.KUBE_CONFIG_DATA }}" | base64 --decode > $HOME/.kube/config
      chmod 600 $HOME/.kube/config
  - name: Update Image Tags in Manifests
    run: |
      IMAGE_TAG="${{ needs.build-and-push.outputs.version }}"
      find k8s/ -name "*.yaml" -o -name "*.yml" | xargs sed -i "s|VERSION_PLACEHOLDER|${IMAGE_TAG}|g"
  - name: Apply Kubernetes Manifests
    run: |
      kubectl apply -f k8s/ --recursive --insecure-skip-tls-verify
```

### Manual Deployment

```bash
# Run complete pipeline locally
make pipeline

# Or run specific stages
./scripts/local-pipeline.sh deploy
```

## 🚨 Troubleshooting

### Common Issues

#### Pod Startup Issues

```bash
# Check pod events
kubectl describe pod -n petrosa-apps -l app=petrosa-ta-bot

# Check pod logs
kubectl logs -n petrosa-apps -l app=petrosa-ta-bot --previous

# Check pod status
kubectl get pods -n petrosa-apps -l app=petrosa-ta-bot -o wide
```

#### Service Connectivity Issues

```bash
# Check service endpoints
kubectl get endpoints -n petrosa-apps petrosa-ta-bot-service

# Test service connectivity
kubectl run test-pod --image=busybox -n petrosa-apps
kubectl exec test-pod -n petrosa-apps -- wget -O- http://petrosa-ta-bot-service

# Check service configuration
kubectl describe service -n petrosa-apps petrosa-ta-bot-service
```

#### Ingress Issues

```bash
# Check ingress status
kubectl describe ingress -n petrosa-apps petrosa-ta-bot-ingress

# Check nginx ingress logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx

# Check SSL certificate
kubectl get certificate -n petrosa-apps ta-bot-tls
```

#### Scaling Issues

```bash
# Check HPA status
kubectl describe hpa petrosa-ta-bot-hpa -n petrosa-apps

# Manual scaling
kubectl scale deployment petrosa-ta-bot --replicas=5 -n petrosa-apps

# Check resource usage
kubectl top pods -n petrosa-apps -l app=petrosa-ta-bot
```

### Diagnostic Commands

```bash
# Check overall cluster health
kubectl get all -n petrosa-apps

# Check events
kubectl get events -n petrosa-apps --sort-by='.lastTimestamp'

# Check resource usage
kubectl top pods -n petrosa-apps
kubectl top nodes

# Check logs
kubectl logs -n petrosa-apps -l app=petrosa-ta-bot -f
```

## 📋 Deployment Checklist

### Pre-Deployment

- [ ] **Namespace**: `petrosa-apps` created
- [ ] **ConfigMaps**: Configuration applied
- [ ] **Secrets**: Sensitive data configured
- [ ] **Network**: NATS and API endpoints accessible
- [ ] **Resources**: Sufficient CPU/memory available
- [ ] **SSL Certificates**: Valid certificates configured

### Deployment

- [ ] **Deployment**: Application deployed
- [ ] **Service**: Network service created
- [ ] **Ingress**: External access configured
- [ ] **HPA**: Auto-scaling enabled
- [ ] **Network Policies**: Security rules applied

### Post-Deployment

- [ ] **Health Checks**: All endpoints responding
- [ ] **Logs**: Application logs accessible
- [ ] **Metrics**: Monitoring data flowing
- [ ] **SSL**: HTTPS working correctly
- [ ] **Scaling**: HPA functioning properly

## 🔗 Related Documentation

- **Deployment Guide**: See [Deployment Guide](./DEPLOYMENT.md) for deployment details
- **Configuration**: Check [Configuration](./CONFIGURATION.md) for environment setup
- **Monitoring**: Review [Monitoring Guide](./MONITORING.md) for observability
- **Troubleshooting**: Read [Troubleshooting](./TROUBLESHOOTING.md) for common issues

---

**Next Steps**:
- Read [Deployment Guide](./DEPLOYMENT.md) for deployment details
- Check [Configuration](./CONFIGURATION.md) for environment setup
- Review [Monitoring Guide](./MONITORING.md) for observability 