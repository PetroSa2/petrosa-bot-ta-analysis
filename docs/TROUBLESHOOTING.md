# Troubleshooting Guide

Comprehensive guide for diagnosing and resolving common issues with the Petrosa TA Bot.

## 🚨 Quick Diagnosis

### Health Check Commands

```bash
# Check application health
curl http://localhost:8000/health

# Check Kubernetes deployment
kubectl get pods -n petrosa-apps -l app=petrosa-ta-bot

# Check logs
kubectl logs -n petrosa-apps -l app=petrosa-ta-bot --tail=50

# Check resource usage
kubectl top pods -n petrosa-apps -l app=petrosa-ta-bot
```

## 🔧 Common Issues & Solutions

### 1. Python Environment Issues

#### Problem: Python Version Mismatch
```bash
# Error: Python 3.11+ required
python3 --version
# Output: Python 3.9.0
```

**Solution**:
```bash
# Install Python 3.11
# macOS
brew install python@3.11

# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv

# Recreate virtual environment
rm -rf .venv
make setup
```

#### Problem: NumPy Compatibility Issues
```bash
# Error: pandas-ta compatibility with NumPy 2.x
ImportError: numpy.ndarray size changed
```

**Solution**:
```bash
# Fix NumPy version
pip install 'numpy<2.0.0'

# Reinstall dependencies
pip install -r requirements.txt
```

#### Problem: Missing Dependencies
```bash
# Error: ModuleNotFoundError
ModuleNotFoundError: No module named 'pandas'
```

**Solution**:
```bash
# Install dependencies
make install-dev

# Or install manually
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Docker Issues

#### Problem: Docker Build Fails
```bash
# Error: Build context error
ERROR: failed to compute cache key
```

**Solution**:
```bash
# Clean Docker cache
make docker-clean

# Rebuild image
make build

# Or force rebuild
docker build --no-cache -t petrosa/ta-bot:latest .
```

#### Problem: Container Won't Start
```bash
# Error: Container exits immediately
docker run petrosa/ta-bot:latest
# Container exits with code 1
```

**Solution**:
```bash
# Check container logs
docker logs $(docker ps -a -q --filter ancestor=petrosa/ta-bot:latest)

# Run with interactive shell
docker run -it petrosa/ta-bot:latest /bin/bash

# Check environment variables
docker run -e NATS_URL=nats://localhost:4222 petrosa/ta-bot:latest
```

#### Problem: Port Already in Use
```bash
# Error: Port 8000 already in use
docker: Error response from daemon: Ports are not available
```

**Solution**:
```bash
# Use different port
docker run -p 8001:8000 petrosa/ta-bot:latest

# Or stop existing container
docker stop $(docker ps -q --filter ancestor=petrosa/ta-bot:latest)
```

### 3. Kubernetes Issues

#### Problem: Cluster Connection Fails
```bash
# Error: Unable to connect to the server
The connection to the server 192.168.194.253:16443 was refused
```

**Solution**:
```bash
# Check kubeconfig
export KUBECONFIG=k8s/kubeconfig.yaml

# Verify cluster info
kubectl cluster-info

# Check network connectivity
ping 192.168.194.253
telnet 192.168.194.253 16443
```

#### Problem: Pods Not Starting
```bash
# Error: Pods in CrashLoopBackOff
kubectl get pods -n petrosa-apps
# NAME                    READY   STATUS             RESTARTS   AGE
# petrosa-ta-bot-xxx     0/1     CrashLoopBackOff   5          10m
```

**Solution**:
```bash
# Check pod events
kubectl describe pod -n petrosa-apps -l app=petrosa-ta-bot

# Check pod logs
kubectl logs -n petrosa-apps -l app=petrosa-ta-bot --previous

# Check ConfigMap and Secrets
kubectl get configmap -n petrosa-apps ta-bot-config
kubectl get secrets -n petrosa-apps ta-bot-secrets
```

#### Problem: Service Not Accessible
```bash
# Error: Service endpoints not found
kubectl get endpoints -n petrosa-apps petrosa-ta-bot-service
# NAME                    ENDPOINTS   AGE
# petrosa-ta-bot-service   <none>      5m
```

**Solution**:
```bash
# Check service configuration
kubectl describe service -n petrosa-apps petrosa-ta-bot-service

# Check pod labels
kubectl get pods -n petrosa-apps --show-labels

# Verify service selector
kubectl get service -n petrosa-apps petrosa-ta-bot-service -o yaml
```

#### Problem: Ingress Not Working
```bash
# Error: Ingress not routing traffic
curl https://ta-bot.petrosa.com/health
# Connection refused
```

**Solution**:
```bash
# Check ingress status
kubectl describe ingress -n petrosa-apps petrosa-ta-bot-ingress

# Check nginx ingress logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx

# Check SSL certificate
kubectl get certificate -n petrosa-apps ta-bot-tls
```

### 4. NATS Connection Issues

#### Problem: NATS Connection Fails
```bash
# Error: NATS connection timeout
nats: no servers available for connection
```

**Solution**:
```bash
# Check NATS server status
nats-server --version

# Test NATS connection
nats-sub "candles.*" &
nats-pub "candles.BTCUSDT" '{"test": "data"}'

# Check environment variables
echo $NATS_URL
```

#### Problem: NATS Authentication Fails
```bash
# Error: NATS authentication failed
nats: authorization violation
```

**Solution**:
```bash
# Check NATS credentials in secrets
kubectl get secret -n petrosa-apps ta-bot-secrets -o yaml

# Update NATS credentials
kubectl create secret generic ta-bot-secrets \
  --from-literal=nats-username="your-username" \
  --from-literal=nats-password="your-password" \
  -n petrosa-apps --dry-run=client -o yaml | kubectl apply -f -
```

### 5. API Connection Issues

#### Problem: REST API Unreachable
```bash
# Error: API endpoint connection failed
requests.exceptions.ConnectionError
```

**Solution**:
```bash
# Test API endpoint
curl -X POST http://api-server:8080/signals \
  -H "Content-Type: application/json" \
  -d '{"test": "signal"}'

# Check API server status
kubectl get pods -n petrosa-apps -l app=api-server

# Verify API endpoint configuration
echo $API_ENDPOINT
```

### 6. Performance Issues

#### Problem: High CPU Usage
```bash
# High CPU usage causing slow performance
kubectl top pods -n petrosa-apps -l app=petrosa-ta-bot
# NAME                    CPU(cores)   MEMORY(bytes)
# petrosa-ta-bot-xxx     500m         512Mi
```

**Solution**:
```bash
# Check HPA status
kubectl get hpa -n petrosa-apps petrosa-ta-bot-hpa

# Scale up manually
kubectl scale deployment petrosa-ta-bot --replicas=5 -n petrosa-apps

# Check resource limits
kubectl describe deployment -n petrosa-apps petrosa-ta-bot
```

#### Problem: Memory Leaks
```bash
# High memory usage
kubectl top pods -n petrosa-apps -l app=petrosa-ta-bot
# NAME                    CPU(cores)   MEMORY(bytes)
# petrosa-ta-bot-xxx     200m         1Gi
```

**Solution**:
```bash
# Check memory usage patterns
kubectl logs -n petrosa-apps -l app=petrosa-ta-bot | grep memory

# Restart pods to clear memory
kubectl rollout restart deployment petrosa-ta-bot -n petrosa-apps

# Increase memory limits
kubectl patch deployment petrosa-ta-bot -n petrosa-apps \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"ta-bot","resources":{"limits":{"memory":"1Gi"}}}]}}}}'
```

### 7. Signal Generation Issues

#### Problem: No Signals Generated
```bash
# No trading signals being produced
kubectl logs -n petrosa-apps -l app=petrosa-ta-bot | grep signal
# No output
```

**Solution**:
```bash
# Check if NATS messages are received
kubectl logs -n petrosa-apps -l app=petrosa-ta-bot | grep "Received candle"

# Check strategy execution
kubectl logs -n petrosa-apps -l app=petrosa-ta-bot | grep "Strategy"

# Verify candle data format
kubectl logs -n petrosa-apps -l app=petrosa-ta-bot | grep "candle"
```

#### Problem: Low Confidence Signals
```bash
# Signals generated but with low confidence
kubectl logs -n petrosa-apps -l app=petrosa-ta-bot | grep "confidence"
# confidence: 0.45
```

**Solution**:
```bash
# Check indicator calculations
kubectl logs -n petrosa-apps -l app=petrosa-ta-bot | grep "indicator"

# Verify market conditions
kubectl logs -n petrosa-apps -l app=petrosa-ta-bot | grep "market"

# Adjust confidence thresholds
# Edit k8s/configmap.yaml
```

## 🔍 Diagnostic Commands

### System Health Checks

```bash
# Check overall system health
make health

# Check Kubernetes resources
kubectl get all -n petrosa-apps

# Check events
kubectl get events -n petrosa-apps --sort-by='.lastTimestamp'

# Check resource usage
kubectl top pods -n petrosa-apps
kubectl top nodes
```

### Network Diagnostics

```bash
# Test NATS connectivity
nats-sub "candles.*" &
nats-pub "candles.BTCUSDT" '{"test": "data"}'

# Test API connectivity
curl -v http://api-server:8080/health

# Test DNS resolution
nslookup ta-bot.petrosa.com
```

### Log Analysis

```bash
# View recent logs
kubectl logs -n petrosa-apps -l app=petrosa-ta-bot --tail=100

# Follow logs in real-time
kubectl logs -n petrosa-apps -l app=petrosa-ta-bot -f

# Search for errors
kubectl logs -n petrosa-apps -l app=petrosa-ta-bot | grep -i error

# Search for warnings
kubectl logs -n petrosa-apps -l app=petrosa-ta-bot | grep -i warn
```

## 🛠️ Recovery Procedures

### Pod Recovery

```bash
# Restart deployment
kubectl rollout restart deployment petrosa-ta-bot -n petrosa-apps

# Check rollout status
kubectl rollout status deployment petrosa-ta-bot -n petrosa-apps

# Rollback if needed
kubectl rollout undo deployment petrosa-ta-bot -n petrosa-apps
```

### Service Recovery

```bash
# Restart service
kubectl delete service petrosa-ta-bot-service -n petrosa-apps
kubectl apply -f k8s/service.yaml

# Check service endpoints
kubectl get endpoints -n petrosa-apps petrosa-ta-bot-service
```

### Ingress Recovery

```bash
# Restart ingress
kubectl delete ingress petrosa-ta-bot-ingress -n petrosa-apps
kubectl apply -f k8s/ingress.yaml

# Check ingress status
kubectl describe ingress -n petrosa-apps petrosa-ta-bot-ingress
```

## 📊 Monitoring & Alerting

### Key Metrics to Monitor

```bash
# Pod status
kubectl get pods -n petrosa-apps -l app=petrosa-ta-bot

# Resource usage
kubectl top pods -n petrosa-apps -l app=petrosa-ta-bot

# Signal generation rate
kubectl logs -n petrosa-apps -l app=petrosa-ta-bot | grep "signal" | wc -l

# Error rate
kubectl logs -n petrosa-apps -l app=petrosa-ta-bot | grep -i error | wc -l
```

### Alerting Rules

```yaml
# Example Prometheus alert rules
groups:
- name: ta-bot-alerts
  rules:
  - alert: TAPodDown
    expr: up{job="petrosa-ta-bot"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "TA Bot pod is down"

  - alert: TAHighErrorRate
    expr: rate(ta_bot_errors_total[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High error rate in TA Bot"

  - alert: TANoSignals
    expr: rate(ta_bot_signals_generated_total[10m]) == 0
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "No signals generated in 10 minutes"
```

## 📞 Getting Help

### Information to Collect

When reporting issues, please include:

1. **Environment Details**:
   ```bash
   kubectl version
   docker version
   python --version
   ```

2. **Error Messages**:
   ```bash
   kubectl logs -n petrosa-apps -l app=petrosa-ta-bot --tail=50
   ```

3. **Configuration**:
   ```bash
   kubectl get configmap -n petrosa-apps ta-bot-config -o yaml
   kubectl get secrets -n petrosa-apps ta-bot-secrets -o yaml
   ```

4. **System Status**:
   ```bash
   kubectl get all -n petrosa-apps
   kubectl top pods -n petrosa-apps
   ```

### Support Channels

- **Documentation**: Check [Architecture Overview](./ARCHITECTURE.md)
- **Configuration**: Review [Deployment Guide](./DEPLOYMENT.md)
- **Development**: See [Development Guide](./DEVELOPMENT.md)

---

**Next Steps**:
- Read [Monitoring Guide](./MONITORING.md) for observability setup
- Check [Security Guide](./SECURITY.md) for security best practices
- Review [Configuration](./CONFIGURATION.md) for environment setup
