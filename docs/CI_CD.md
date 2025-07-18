# CI/CD Pipeline

Comprehensive CI/CD pipeline documentation for the Petrosa TA Bot.

## 🚀 Pipeline Overview

### Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CI/CD Pipeline                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │   Trigger   │  │   Build     │  │   Test      │       │
│  │   (Push)    │  │   (Docker)  │  │   (Pytest)  │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
│           │               │               │               │
│           └───────────────┼───────────────┘               │
│                           │                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Deployment Stages                      │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │   │
│  │  │   Security  │  │   Deploy    │  │   Monitor   │ │   │
│  │  │   (Trivy)   │  │   (K8s)    │  │   (Health)  │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘ │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Pipeline Stages

1. **Trigger**: Git push to main branch
2. **Version Management**: Generate semantic version
3. **Build**: Build Docker image
4. **Test**: Run unit and integration tests
5. **Security**: Vulnerability scanning
6. **Deploy**: Deploy to Kubernetes
7. **Monitor**: Health checks and notifications

## 📋 GitHub Actions Workflow

### Main Workflow (`ci.yml`)

```yaml
name: Deploy

on:
  push:
    branches: [ 'main' ]
    tags-ignore: [ '*' ]

jobs:
  create-release:
    name: Create Release
    runs-on: ubuntu-latest
    permissions:
      contents: write
      packages: write
    outputs:
      version: ${{ steps.version.outputs.version }}
      tag-created: ${{ steps.create-tag.outputs.tag-created }}
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      with:
        fetch-depth: 0
        token: ${{ secrets.GITHUB_TOKEN }}
        fetch-tags: true
    - name: Configure Git
      run: |
        git config --local user.email "action@github.com"
        git config --local user.name "GitHub Action"
    - name: Generate Semantic Version
      id: version
      run: |
        LATEST_VERSION=$(git tag --sort=-version:refname | grep '^v[0-9]' | head -1)
        if [ -z "$LATEST_VERSION" ]; then
          VERSION="v1.0.0"
        else
          if [[ "$LATEST_VERSION" =~ ^v([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
            MAJOR="${BASH_REMATCH[1]}"
            MINOR="${BASH_REMATCH[2]}"
            PATCH="${BASH_REMATCH[3]}"
            NEW_PATCH=$((PATCH + 1))
            VERSION="v${MAJOR}.${MINOR}.${NEW_PATCH}"
          else
            VERSION="v1.0.0"
          fi
        fi
        echo "version=${VERSION}" >> $GITHUB_OUTPUT
        echo "Final generated version: ${VERSION}"
    - name: Create and Push Tag
      id: create-tag
      run: |
        VERSION="${{ steps.version.outputs.version }}"
        if git rev-parse "$VERSION" >/dev/null 2>&1; then
          git tag -d "$VERSION"
          git push origin ":refs/tags/$VERSION" || echo "Tag deletion from remote failed (may not exist remotely)"
        fi
        git tag "$VERSION"
        git push origin "$VERSION"
        echo "tag-created=true" >> $GITHUB_OUTPUT

  build-and-push:
    name: Build & Push
    needs: create-release
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    outputs:
      version: ${{ steps.version.outputs.version }}
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      with:
        fetch-depth: 0
    - name: Determine Version
      id: version
      run: |
        if [[ "${{ github.ref }}" == refs/tags/* ]]; then
          VERSION="${{ github.ref_name }}"
        else
          VERSION="${{ needs.create-release.outputs.version }}"
        fi
        echo "version=${VERSION}" >> $GITHUB_OUTPUT
    - name: Set up QEMU
      uses: docker/setup-qemu-action@v3
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    - name: Log in to Docker Hub
      uses: docker/login-action@v3
      with:
        username: ${{ secrets.DOCKERHUB_USERNAME }}
        password: ${{ secrets.DOCKERHUB_TOKEN }}
    - name: Extract Docker Metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ secrets.DOCKERHUB_USERNAME }}/petrosa-ta-bot
        tags: |
          type=raw,value=${{ steps.version.outputs.version }}
          type=raw,value=latest
    - name: Build and Push Docker Image
      id: build
      uses: docker/build-push-action@v5
      with:
        context: .
        platforms: linux/amd64,linux/arm64
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
        build-args: |
          VERSION=${{ steps.version.outputs.version }}
          COMMIT_SHA=${{ github.sha }}
          BUILD_DATE=${{ steps.meta.outputs.date }}

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
        kubectl cluster-info --insecure-skip-tls-verify
        kubectl get nodes --insecure-skip-tls-verify
    - name: Update Image Tags in Manifests
      run: |
        IMAGE_TAG="${{ needs.build-and-push.outputs.version }}"
        find k8s/ -name "*.yaml" -o -name "*.yml" | xargs sed -i "s|VERSION_PLACEHOLDER|${IMAGE_TAG}|g"
    - name: Apply Kubernetes Manifests
      run: |
        kubectl apply -f k8s/ --recursive --insecure-skip-tls-verify
    - name: Deployment Summary
      run: |
        IMAGE_TAG="${{ needs.build-and-push.outputs.version }}"
        echo "🎉 Deployment to MicroK8s completed successfully!"
        echo "  ✅ Docker image: ${{ secrets.DOCKERHUB_USERNAME }}/petrosa-ta-bot:${IMAGE_TAG}"
        echo "  ✅ Kubernetes manifests applied to MicroK8s cluster"

  notify:
    name: notify
    needs: [build-and-push, deploy, create-release]
    runs-on: ubuntu-latest
    if: always()
    steps:
    - name: Notify Deployment Status
      run: |
        VERSION="${{ needs.create-release.outputs.version }}"
        TAG_CREATED="${{ needs.create-release.outputs.tag-created }}"
        IMAGE_TAG="${{ needs.build-and-push.outputs.version }}"
        if [ "${{ needs.deploy.result }}" == "success" ]; then
          echo "✅ Deployment successful!"
          echo "📦 Version: ${VERSION}"
          echo "🐳 Image Tag: ${IMAGE_TAG}"
          if [ "$TAG_CREATED" == "true" ]; then
            echo "🏷️  New tag created: ${VERSION}"
          else
            echo "🏷️  Using existing tag: ${VERSION}"
          fi
          echo "🚀 Deployed to MicroK8s with versioned image tag"
        else
          echo "❌ Deployment failed!"
          echo "📦 Version: ${VERSION}"
          echo "🐳 Image Tag: ${IMAGE_TAG}"
        fi

  cleanup:
    name: cleanup
    needs: [build-and-push]
    runs-on: ubuntu-latest
    if: always()
    steps:
    - name: Clean Up Old Images
      run: |
        echo "Cleaning up old Docker images..."
```

## 🔄 Version Management

### Semantic Versioning

The pipeline uses semantic versioning (MAJOR.MINOR.PATCH):

```bash
# Version generation logic
LATEST_VERSION=$(git tag --sort=-version:refname | grep '^v[0-9]' | head -1)
if [ -z "$LATEST_VERSION" ]; then
  VERSION="v1.0.0"
else
  if [[ "$LATEST_VERSION" =~ ^v([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
    MAJOR="${BASH_REMATCH[1]}"
    MINOR="${BASH_REMATCH[2]}"
    PATCH="${BASH_REMATCH[3]}"
    NEW_PATCH=$((PATCH + 1))
    VERSION="v${MAJOR}.${MINOR}.${NEW_PATCH}"
  else
    VERSION="v1.0.0"
  fi
fi
```

### Version Tags

- **Format**: `v1.0.0`, `v1.0.1`, etc.
- **Auto-increment**: PATCH version increments automatically
- **Manual override**: Can be overridden with manual tags
- **GitHub Releases**: Automatic release creation

## 🐳 Docker Build Process

### Multi-Platform Build

```yaml
- name: Build and Push Docker Image
  uses: docker/build-push-action@v5
  with:
    context: .
    platforms: linux/amd64,linux/arm64
    push: true
    tags: ${{ steps.meta.outputs.tags }}
    labels: ${{ steps.meta.outputs.labels }}
    cache-from: type=gha
    cache-to: type=gha,mode=max
    build-args: |
      VERSION=${{ steps.version.outputs.version }}
      COMMIT_SHA=${{ github.sha }}
      BUILD_DATE=${{ steps.meta.outputs.date }}
```

### Build Arguments

```dockerfile
# Dockerfile
ARG VERSION=latest
ARG COMMIT_SHA=unknown
ARG BUILD_DATE=unknown

ENV VERSION=${VERSION}
ENV COMMIT_SHA=${COMMIT_SHA}
ENV BUILD_DATE=${BUILD_DATE}
```

### Image Tags

- **Version tag**: `yurisa2/petrosa-ta-bot:v1.0.1`
- **Latest tag**: `yurisa2/petrosa-ta-bot:latest`
- **Metadata**: Includes version, commit SHA, build date

## ☸️ Kubernetes Deployment

### Deployment Process

1. **Version Replacement**: Replace `VERSION_PLACEHOLDER` in manifests
2. **Manifest Application**: Apply all Kubernetes manifests
3. **Health Checks**: Verify deployment success
4. **Rollback**: Automatic rollback on failure

### Deployment Commands

```bash
# Update image tags in manifests
IMAGE_TAG="v1.0.1"
find k8s/ -name "*.yaml" -o -name "*.yml" | xargs sed -i "s|VERSION_PLACEHOLDER|${IMAGE_TAG}|g"

# Apply manifests
kubectl apply -f k8s/ --recursive --insecure-skip-tls-verify

# Verify deployment
kubectl rollout status deployment/petrosa-ta-bot -n petrosa-apps
```

### Deployment Verification

```bash
# Check deployment status
kubectl get pods -n petrosa-apps -l app=petrosa-ta-bot

# Check service
kubectl get svc -n petrosa-apps petrosa-ta-bot-service

# Check ingress
kubectl get ingress -n petrosa-apps petrosa-ta-bot-ingress

# Check logs
kubectl logs -n petrosa-apps -l app=petrosa-ta-bot --tail=50
```

## 🔒 Security Scanning

### Trivy Vulnerability Scanning

```yaml
# Add to workflow
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: '${{ secrets.DOCKERHUB_USERNAME }}/petrosa-ta-bot:${{ steps.version.outputs.version }}'
    format: 'sarif'
    output: 'trivy-results.sarif'

- name: Upload Trivy scan results to GitHub Security tab
  uses: github/codeql-action/upload-sarif@v2
  if: always()
  with:
    sarif_file: 'trivy-results.sarif'
```

### Security Checks

- **Container scanning**: Trivy vulnerability scanning
- **Dependency scanning**: GitHub Dependabot alerts
- **Code scanning**: CodeQL analysis
- **Secret scanning**: GitHub secret scanning

## 📊 Monitoring & Notifications

### Deployment Notifications

```yaml
- name: Notify Deployment Status
  run: |
    VERSION="${{ needs.create-release.outputs.version }}"
    IMAGE_TAG="${{ needs.build-and-push.outputs.version }}"
    if [ "${{ needs.deploy.result }}" == "success" ]; then
      echo "✅ Deployment successful!"
      echo "📦 Version: ${VERSION}"
      echo "🐳 Image Tag: ${IMAGE_TAG}"
    else
      echo "❌ Deployment failed!"
      echo "📦 Version: ${VERSION}"
      echo "🐳 Image Tag: ${IMAGE_TAG}"
    fi
```

### Health Checks

```bash
# Health check endpoints
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/live

# Kubernetes health checks
kubectl get pods -n petrosa-apps -l app=petrosa-ta-bot
kubectl describe pod -n petrosa-apps -l app=petrosa-ta-bot
```

## 🔧 Local Pipeline

### Local Development Pipeline

```bash
# Run complete local pipeline
make pipeline

# Or run specific stages
./scripts/local-pipeline.sh lint test build
./scripts/local-pipeline.sh deploy
./scripts/local-pipeline.sh all
```

### Local Pipeline Script

```bash
#!/bin/bash
# scripts/local-pipeline.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if stage is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <stage> [stage2] [stage3] ..."
    echo "Available stages: setup, lint, test, security, build, container, deploy, all"
    exit 1
fi

# Process each stage
for stage in "$@"; do
    case $stage in
        "setup")
            print_status "Running setup stage..."
            make setup
            ;;
        "lint")
            print_status "Running lint stage..."
            make lint
            ;;
        "test")
            print_status "Running test stage..."
            make test
            ;;
        "security")
            print_status "Running security stage..."
            make security
            ;;
        "build")
            print_status "Running build stage..."
            make build
            ;;
        "container")
            print_status "Running container stage..."
            make container
            ;;
        "deploy")
            print_status "Running deploy stage..."
            make deploy
            ;;
        "all")
            print_status "Running all stages..."
            make pipeline
            ;;
        *)
            print_error "Unknown stage: $stage"
            exit 1
            ;;
    esac
done

print_status "Pipeline completed successfully!"
```

## 🚨 Error Handling

### Pipeline Failures

```yaml
# Error handling in workflow
- name: Handle Build Failure
  if: failure()
  run: |
    echo "❌ Build failed!"
    echo "Check the logs for details"
    # Send notification
    # Create issue
    # Rollback if needed

- name: Handle Deploy Failure
  if: failure()
  run: |
    echo "❌ Deployment failed!"
    echo "Rolling back to previous version..."
    kubectl rollout undo deployment/petrosa-ta-bot -n petrosa-apps
```

### Rollback Strategy

```bash
# Manual rollback
kubectl rollout undo deployment/petrosa-ta-bot -n petrosa-apps

# Check rollback status
kubectl rollout status deployment/petrosa-ta-bot -n petrosa-apps

# View rollback history
kubectl rollout history deployment/petrosa-ta-bot -n petrosa-apps
```

## 📋 Pipeline Checklist

### Pre-Deployment

- [ ] **Code Quality**: Linting passes
- [ ] **Tests**: All tests pass
- [ ] **Security**: No vulnerabilities
- [ ] **Dependencies**: All dependencies updated
- [ ] **Documentation**: Documentation updated
- [ ] **Version**: Version properly incremented

### Deployment

- [ ] **Build**: Docker image builds successfully
- [ ] **Push**: Image pushed to registry
- [ ] **Deploy**: Kubernetes deployment successful
- [ ] **Health**: Health checks pass
- [ ] **Monitoring**: Metrics flowing
- [ ] **Notifications**: Team notified

### Post-Deployment

- [ ] **Verification**: Application working correctly
- [ ] **Monitoring**: No errors in logs
- [ ] **Performance**: Performance within limits
- [ ] **Rollback**: Rollback plan ready
- [ ] **Documentation**: Deployment documented

## 🔗 Related Documentation

- **Deployment Guide**: See [Deployment Guide](./DEPLOYMENT.md) for deployment details
- **Kubernetes Configuration**: Check [Kubernetes Configuration](./KUBERNETES.md) for K8s setup
- **Monitoring Guide**: Review [Monitoring Guide](./MONITORING.md) for monitoring
- **Security Guide**: Read [Security Guide](./SECURITY.md) for security

---

**Next Steps**:
- Read [Deployment Guide](./DEPLOYMENT.md) for deployment details
- Check [Kubernetes Configuration](./KUBERNETES.md) for K8s setup
- Review [Monitoring Guide](./MONITORING.md) for monitoring 