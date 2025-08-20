# Installation Guide

Complete setup instructions for the Petrosa TA Bot.

## 🚀 Prerequisites

### System Requirements

- **Python 3.11+**: Required for development and runtime
- **Docker**: Required for containerization and local testing
- **kubectl**: Required for Kubernetes deployment (remote cluster)
- **Make**: Required for using the Makefile commands
- **Git**: For version control

### Operating System Support

- **macOS**: 10.15+ (Catalina)
- **Ubuntu**: 20.04+ / 22.04+
- **CentOS/RHEL**: 8+
- **Windows**: WSL2 recommended

## 📦 Installation Methods

### Method 1: Quick Setup (Recommended)

```bash
# Clone the repository
git clone https://github.com/petrosa/ta-bot.git
cd ta-bot

# Complete automated setup
make setup
```

### Method 2: Manual Setup

```bash
# Clone the repository
git clone https://github.com/petrosa/ta-bot.git
cd ta-bot

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

## 🔧 Environment Configuration

### 1. Copy Environment Template

```bash
# Copy environment template
cp env.example .env

# Edit configuration
nano .env
```

### 2. Required Environment Variables

```bash
# Core Configuration
NATS_URL=nats://localhost:4222
TA_BOT_API_ENDPOINT=http://localhost:8080/signals
TA_BOT_LOG_LEVEL=INFO
TA_BOT_ENVIRONMENT=development

# Trading Configuration
TA_BOT_SUPPORTED_SYMBOLS=BTCUSDT,ETHUSDT,ADAUSDT
TA_BOT_SUPPORTED_TIMEFRAMES=15m,1h

# Optional Configuration
DEBUG=false
SIMULATION_MODE=false
```

### 3. Development Configuration

```bash
# Development-specific settings
LOG_LEVEL=DEBUG
ENVIRONMENT=development
SUPPORTED_SYMBOLS=BTCUSDT,ETHUSDT
SUPPORTED_TIMEFRAMES=15m,1h
```

## 🐳 Docker Installation

### Install Docker

#### macOS
```bash
# Using Homebrew
brew install --cask docker

# Or download from Docker Desktop
# https://www.docker.com/products/docker-desktop
```

#### Ubuntu/Debian
```bash
# Update package index
sudo apt-get update

# Install prerequisites
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Set up stable repository
echo \
  "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

# Add user to docker group
sudo usermod -aG docker $USER
```

#### CentOS/RHEL
```bash
# Install Docker
sudo yum install -y docker

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER
```

### Verify Docker Installation

```bash
# Check Docker version
docker --version

# Test Docker
docker run hello-world
```

## ☸️ Kubernetes Installation

### Install kubectl

#### macOS
```bash
# Using Homebrew
brew install kubectl

# Or download binary
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/darwin/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/
```

#### Linux
```bash
# Download kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/
```

### Configure Remote Cluster Access

```bash
# Set kubeconfig for remote MicroK8s cluster
export KUBECONFIG=k8s/kubeconfig.yaml

# Verify connection
kubectl cluster-info
kubectl get nodes
```

## 🛠️ Development Tools

### Install Additional Tools

```bash
# Install development tools
make install-tools
```

This will install:
- **Trivy**: Container vulnerability scanner
- **jq**: JSON processor
- **pre-commit**: Git hooks

### Manual Tool Installation

#### Trivy (Security Scanner)
```bash
# macOS
brew install trivy

# Ubuntu/Debian
sudo apt-get install wget apt-transport-https gnupg lsb-release
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
echo deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main | sudo tee -a /etc/apt/sources.list.d/trivy.list
sudo apt-get update
sudo apt-get install trivy
```

#### jq (JSON Processor)
```bash
# macOS
brew install jq

# Ubuntu/Debian
sudo apt-get install jq

# CentOS/RHEL
sudo yum install jq
```

## 🔍 Verification

### 1. Check Python Environment

```bash
# Verify Python version
python3 --version
# Should be Python 3.11+

# Check virtual environment
which python
# Should point to .venv/bin/python
```

### 2. Verify Dependencies

```bash
# Check installed packages
pip list

# Verify key packages
python -c "import pandas, numpy, nats, fastapi; print('All dependencies installed')"
```

### 3. Test Docker

```bash
# Build Docker image
make build

# Test container
make container
```

### 4. Test Kubernetes Connection

```bash
# Check cluster connection
kubectl cluster-info

# Check namespace
kubectl get namespace petrosa-apps
```

## 🚨 Troubleshooting

### Common Installation Issues

#### Python Version Issues
```bash
# Check Python version
python3 --version

# If version < 3.11, install Python 3.11
# macOS
brew install python@3.11

# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv
```

#### Docker Permission Issues
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in, or run:
newgrp docker
```

#### Kubernetes Connection Issues
```bash
# Check kubeconfig
ls -la k8s/kubeconfig.yaml

# Test connection
kubectl --kubeconfig=k8s/kubeconfig.yaml cluster-info
```

#### NumPy Compatibility Issues
```bash
# Fix NumPy version for pandas-ta compatibility
pip install 'numpy<2.0.0'

# Reinstall dependencies
pip install -r requirements.txt
```

## 📋 Installation Checklist

- [ ] **Python 3.11+** installed and verified
- [ ] **Virtual environment** created and activated
- [ ] **Dependencies** installed (`requirements.txt` and `requirements-dev.txt`)
- [ ] **Docker** installed and working
- [ ] **kubectl** installed and configured
- [ ] **Environment variables** configured
- [ ] **Pre-commit hooks** installed
- [ ] **Development tools** installed (Trivy, jq)
- [ ] **Kubernetes connection** verified
- [ ] **Docker build** successful
- [ ] **Tests passing** (`make test`)

## 🎯 Next Steps

After successful installation:

1. **Read [Quick Start Guide](./QUICK_START.md)** for immediate usage
2. **Review [Configuration](./CONFIGURATION.md)** for detailed settings
3. **Check [Development Guide](./DEVELOPMENT.md)** for development workflow
4. **Follow [Deployment Guide](./DEPLOYMENT.md)** for production deployment

---

**Need Help?**
- Check [Troubleshooting Guide](./TROUBLESHOOTING.md)
- Review [Architecture Overview](./ARCHITECTURE.md)
- See [Configuration](./CONFIGURATION.md) for environment setup
