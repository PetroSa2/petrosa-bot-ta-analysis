# Deployment Guide

Complete guide for deploying the Petrosa TA Bot to production environments.

## 🚀 Deployment Overview

### Deployment Options

| Environment | Method | Use Case | Complexity |
|-------------|--------|----------|------------|
| **Local** | Docker | Development/Testing | Low |
| **Staging** | Kubernetes | Pre-production | Medium |
| **Production** | Kubernetes | Live trading | High |

### Prerequisites

- **Python 3.11+** for local development
- **Docker** for containerization
- **kubectl** for Kubernetes deployment
- **Remote MicroK8s cluster** access
- **NATS server** running
- **REST API endpoint** for signals

## 🐳 Local Deployment

### Docker Deployment

```bash
# Build Docker image
make build

# Run container locally
docker run -p 8000:8000 \
  -e NATS_URL=nats://localhost:4222 \
  -e API_ENDPOINT=http://localhost:8080/signals \
  petrosa/ta-bot:latest
```

### Environment Configuration

```bash
# Copy environment template
cp env.example .env

# Edit configuration
nano .env
```

**Required Environment Variables**:
```bash
NATS_URL=nats://localhost:4222
API_ENDPOINT=http://localhost:8080/signals
LOG_LEVEL=INFO
ENVIRONMENT=development
```

### Health Checks

```bash
# Test health endpoints
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/live
```

## ☸️ Kubernetes Deployment

### Remote Cluster Setup

The TA Bot uses a **remote MicroK8s cluster** - no local Kubernetes installation required.

#### Cluster Configuration
- **Server**: `https://192.168.194.253:16443`
- **Namespace**: `petrosa-apps`
- **Context**: `microk8s-context`

#### Connection Setup

```bash
# Set kubeconfig for remote cluster
export KUBECONFIG=k8s/kubeconfig.yaml

# Verify connection
kubectl cluster-info
kubectl get nodes
```

### Production Deployment

#### 1. Create Namespace

```bash
# Create namespace if it doesn't exist
kubectl create namespace petrosa-apps
```

#### 2. Apply Kubernetes Manifests

```bash
# Apply all manifests
kubectl apply -f k8s/

# Or apply individually
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml
```

#### 3. Verify Deployment

```bash
# Check deployment status
kubectl get pods -n petrosa-apps -l app=petrosa-ta-bot

# Check services
kubectl get svc -n petrosa-apps -l app=petrosa-ta-bot

# Check ingress
kubectl get ingress -n petrosa-apps -l app=petrosa-ta-bot
```

### Deployment Components

#### 1. **ConfigMap** (`k8s/configmap.yaml`)
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ta-bot-config
  namespace: petrosa-apps
data:
  nats_url: "nats://nats-server:4222"
  api_endpoint: "http://api-server:8080/signals"
  log_level: "INFO"
  environment: "production"
```

#### 2. **Secrets** (`k8s/secrets.yaml`)
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: ta-bot-secrets
  namespace: petrosa-apps
type: Opaque
data:
  nats_username: ""  # Base64 encoded
  nats_password: ""  # Base64 encoded
  api_auth_token: "" # Base64 encoded
```

#### 3. **Deployment** (`k8s/deployment.yaml`)
- **Replicas**: 3 (configurable)
- **Resources**: CPU/memory limits
- **Health Checks**: Liveness/readiness probes
- **Environment**: ConfigMap and Secret references

#### 4. **Service** (`k8s/service.yaml`)
- **Type**: ClusterIP
- **Port**: 80 → 8000
- **Selector**: `app=petrosa-ta-bot`

#### 5. **Ingress** (`k8s/ingress.yaml`)
- **SSL**: Let's Encrypt certificates
- **Host**: `ta-bot.petrosa.com`
- **Annotations**: Nginx ingress class

#### 6. **HPA** (`k8s/hpa.yaml`)
- **Min Replicas**: 2
- **Max Replicas**: 10
- **CPU Target**: 70%
- **Memory Target**: 80%

### Deployment Verification

#### Health Check Commands

```bash
# Check pod status
kubectl get pods -n petrosa-apps -l app=petrosa-ta-bot

# Check pod logs
kubectl logs -n petrosa-apps -l app=petrosa-ta-bot --tail=50

# Check service endpoints
kubectl get endpoints -n petrosa-apps petrosa-ta-bot-service

# Test health endpoints
kubectl port-forward -n petrosa-apps svc/petrosa-ta-bot-service 8000:80
curl http://localhost:8000/health
```

#### Monitoring Commands

```bash
# Check HPA status
kubectl get hpa -n petrosa-apps petrosa-ta-bot-hpa

# Check resource usage
kubectl top pods -n petrosa-apps -l app=petrosa-ta-bot

# Check events
kubectl get events -n petrosa-apps --sort-by='.lastTimestamp'
```

## 🔄 CI/CD Deployment

### GitHub Actions Pipeline

The deployment is automated via GitHub Actions:

#### Staging Deployment
- **Trigger**: Push to `develop` branch
- **Environment**: `staging`
- **Cluster**: Remote MicroK8s staging

#### Production Deployment
- **Trigger**: Push to `main` branch
- **Environment**: `production`
- **Cluster**: Remote MicroK8s production

### Manual Deployment

```bash
# Run complete pipeline locally
make pipeline

# Or run specific stages
./scripts/local-pipeline.sh deploy
```

### Rollback Procedures

```bash
# Rollback to previous version
kubectl rollout undo deployment/petrosa-ta-bot -n petrosa-apps

# Check rollout status
kubectl rollout status deployment/petrosa-ta-bot -n petrosa-apps

# View rollout history
kubectl rollout history deployment/petrosa-ta-bot -n petrosa-apps
```

## 🔧 Configuration Management

### Environment Variables

#### Required for Production
```bash
NATS_URL=nats://nats-server:4222
API_ENDPOINT=http://api-server:8080/signals
LOG_LEVEL=INFO
ENVIRONMENT=production
```

#### Optional Configuration
```bash
SUPPORTED_SYMBOLS=BTCUSDT,ETHUSDT,ADAUSDT
SUPPORTED_TIMEFRAMES=15m,1h
DEBUG=false
SIMULATION_MODE=false
```

### Kubernetes ConfigMaps

```bash
# Create configmap from file
kubectl create configmap ta-bot-config \
  --from-file=k8s/configmap.yaml \
  -n petrosa-apps

# Update configmap
kubectl apply -f k8s/configmap.yaml
```

### Kubernetes Secrets

```bash
# Create secrets (replace with actual values)
kubectl create secret generic ta-bot-secrets \
  --from-literal=nats-username="your-username" \
  --from-literal=nats-password="your-password" \
  --from-literal=api-auth-token="your-token" \
  -n petrosa-apps
```

## 📊 Monitoring & Observability

### Health Endpoints

```bash
# Health check
curl https://ta-bot.petrosa.com/health

# Readiness probe
curl https://ta-bot.petrosa.com/ready

# Liveness probe
curl https://ta-bot.petrosa.com/live
```

### Metrics Collection

```bash
# Prometheus metrics
curl https://ta-bot.petrosa.com/metrics

# Application logs
kubectl logs -n petrosa-apps -l app=petrosa-ta-bot -f
```

### Alerting Setup

```yaml
# Example Prometheus alert rule
groups:
- name: ta-bot-alerts
  rules:
  - alert: TASignalEngineDown
    expr: up{job="petrosa-ta-bot"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "TA Bot is down"
```

## 🔒 Security Configuration

### Network Security

#### Network Policies
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
```

#### RBAC Configuration
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
```

### TLS Configuration

#### SSL Certificate
```bash
# Verify certificate
kubectl get certificate -n petrosa-apps ta-bot-tls

# Check certificate status
kubectl describe certificate ta-bot-tls -n petrosa-apps
```

## 🚨 Troubleshooting

### Common Deployment Issues

#### 1. Pod Startup Issues
```bash
# Check pod events
kubectl describe pod -n petrosa-apps -l app=petrosa-ta-bot

# Check pod logs
kubectl logs -n petrosa-apps -l app=petrosa-ta-bot --previous
```

#### 2. Service Connectivity Issues
```bash
# Check service endpoints
kubectl get endpoints -n petrosa-apps petrosa-ta-bot-service

# Test service connectivity
kubectl run test-pod --image=busybox -n petrosa-apps
kubectl exec test-pod -n petrosa-apps -- wget -O- http://petrosa-ta-bot-service
```

#### 3. Ingress Issues
```bash
# Check ingress status
kubectl describe ingress -n petrosa-apps petrosa-ta-bot-ingress

# Check nginx ingress logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx
```

### Performance Issues

#### Resource Constraints
```bash
# Check resource usage
kubectl top pods -n petrosa-apps -l app=petrosa-ta-bot

# Check HPA status
kubectl get hpa -n petrosa-apps petrosa-ta-bot-hpa
```

#### Scaling Issues
```bash
# Manual scaling
kubectl scale deployment petrosa-ta-bot --replicas=5 -n petrosa-apps

# Check scaling events
kubectl describe hpa petrosa-ta-bot-hpa -n petrosa-apps
```

## 📋 Deployment Checklist

### Pre-Deployment
- [ ] **Environment Variables**: All required variables configured
- [ ] **Secrets**: NATS credentials and API tokens set
- [ ] **Network**: NATS server and API endpoint accessible
- [ ] **Resources**: Sufficient CPU/memory available
- [ ] **SSL Certificates**: Valid certificates configured

### Deployment
- [ ] **Namespace**: `petrosa-apps` created
- [ ] **ConfigMaps**: Configuration applied
- [ ] **Secrets**: Sensitive data configured
- [ ] **Deployment**: Application deployed
- [ ] **Service**: Network service created
- [ ] **Ingress**: External access configured
- [ ] **HPA**: Auto-scaling enabled

### Post-Deployment
- [ ] **Health Checks**: All endpoints responding
- [ ] **Logs**: Application logs accessible
- [ ] **Metrics**: Monitoring data flowing
- [ ] **SSL**: HTTPS working correctly
- [ ] **Scaling**: HPA functioning properly

## 🔄 Maintenance

### Regular Maintenance Tasks

#### Daily
- [ ] Check application logs for errors
- [ ] Monitor resource usage
- [ ] Verify signal generation

#### Weekly
- [ ] Review performance metrics
- [ ] Check certificate expiration
- [ ] Update dependencies if needed

#### Monthly
- [ ] Performance analysis
- [ ] Security updates
- [ ] Backup verification

---

**Next Steps**:
- Read [Kubernetes Configuration](./KUBERNETES.md) for detailed K8s setup
- Check [Monitoring Guide](./MONITORING.md) for observability setup
- Review [Troubleshooting](./TROUBLESHOOTING.md) for common issues
