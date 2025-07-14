# GitHub Actions Setup Guide

This guide explains how to set up the GitHub Actions CI/CD pipeline for the TA Bot service.

## Overview

The pipeline includes:
- **Linting and Testing**: Code quality checks and unit tests
- **Security Scanning**: Vulnerability scanning with Trivy
- **Automatic Versioning**: Semantic version management
- **Docker Builds**: Multi-architecture Docker image builds
- **Kubernetes Deployment**: Automatic deployment to MicroK8s cluster

## Required GitHub Secrets

The pipeline requires the following secrets to be configured in your GitHub repository:

### 1. Docker Hub Credentials
- **DOCKERHUB_USERNAME**: Your Docker Hub username
- **DOCKERHUB_TOKEN**: Your Docker Hub access token

**To create a Docker Hub token:**
1. Log in to Docker Hub
2. Go to Account Settings → Security
3. Click "New Access Token"
4. Give it a name (e.g., "GitHub Actions")
5. Copy the token and add it to GitHub secrets

### 2. Kubernetes Configuration
- **KUBE_CONFIG_DATA**: Base64-encoded kubeconfig for your MicroK8s cluster

**To create the kubeconfig:**
```bash
# Encode your kubeconfig file
cat k8s/kubeconfig.yaml | base64 -w 0
```

### 3. Optional Secrets
- **CODECOV_TOKEN**: For code coverage reporting (optional)

## Setting Up GitHub Secrets

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret with the exact names listed above

## Pipeline Workflow

### 1. Lint and Test Job
- Runs on every push and pull request
- Performs code quality checks (flake8, mypy, ruff)
- Runs unit tests with coverage reporting
- Uploads coverage to Codecov (if token provided)

### 2. Security Scan Job
- Runs Trivy vulnerability scanner
- Checks for security vulnerabilities in dependencies
- Fails the pipeline if critical vulnerabilities are found

### 3. Create Release Job (Main Branch Only)
- Generates semantic version based on git tags
- Creates and pushes new version tags
- Handles automatic version incrementing

### 4. Build and Push Job (Main Branch Only)
- Builds multi-architecture Docker images
- Pushes to Docker Hub (if credentials available)
- Falls back to local build if Docker Hub credentials missing

### 5. Deploy Job (Main Branch Only)
- Updates Kubernetes manifests with versioned image tags
- Deploys to MicroK8s cluster
- Verifies deployment status

## Troubleshooting Common Issues

### 1. Docker Hub Authentication Failures

**Error**: `unauthorized: authentication required`

**Solution**:
1. Verify `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` are set correctly
2. Ensure the Docker Hub token has the correct permissions
3. Check that the token hasn't expired

**Fallback**: The pipeline will build a local image if Docker Hub credentials are missing

### 2. Kubernetes Connection Failures

**Error**: `Unable to connect to the server`

**Solution**:
1. Verify `KUBE_CONFIG_DATA` is properly base64-encoded
2. Check that the kubeconfig points to the correct cluster
3. Ensure the cluster is accessible from GitHub Actions

**Fallback**: The pipeline will skip deployment if Kubernetes configuration is missing

### 3. Image Pull Failures

**Error**: `Failed to pull image`

**Solution**:
1. Check that the Docker image exists in Docker Hub
2. Verify the image tag is correct
3. Ensure the cluster has access to Docker Hub

### 4. Version Generation Issues

**Error**: `No previous version found`

**Solution**:
1. Check that git tags are properly formatted (v1.0.0, v1.0.1, etc.)
2. Ensure the repository has proper git history
3. Verify that the GitHub token has sufficient permissions

### 5. Coverage Upload Failures

**Error**: `Codecov upload failed`

**Solution**:
1. Add `CODECOV_TOKEN` secret (optional)
2. The pipeline will continue even if Codecov upload fails

## Manual Deployment

If the automated deployment fails, you can deploy manually:

```bash
# Set up kubectl
export KUBECONFIG=k8s/kubeconfig.yaml

# Apply manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n petrosa-apps -l app=petrosa-ta-bot
```

## Monitoring Deployments

### Check Pipeline Status
1. Go to your GitHub repository
2. Click **Actions** tab
3. View the latest workflow run

### Check Deployment Status
```bash
# Check pods
kubectl get pods -n petrosa-apps -l app=petrosa-ta-bot

# Check deployment
kubectl get deployment petrosa-ta-bot -n petrosa-apps

# View logs
kubectl logs -l app=petrosa-ta-bot -n petrosa-apps --tail=100
```

### Check Docker Images
```bash
# List local images
docker images | grep petrosa-ta-bot

# Pull from Docker Hub (if available)
docker pull your-username/petrosa-ta-bot:latest
```

## Pipeline Configuration

### Environment Variables
- `PYTHON_VERSION`: Python version to use (3.11)
- `REGISTRY`: Docker registry (docker.io)
- `IMAGE_NAME`: Docker image name

### Triggers
- **Push to main/develop**: Runs full pipeline
- **Pull requests**: Runs lint and test only
- **Tags**: Runs full pipeline with tag version

### Conditional Steps
- Docker build/push: Only if Docker Hub credentials available
- Kubernetes deployment: Only if kubeconfig available
- Codecov upload: Only if token provided

## Security Considerations

1. **Secrets Management**: All sensitive data is stored as GitHub secrets
2. **Base64 Encoding**: Kubernetes config is base64-encoded for security
3. **Token Permissions**: Use minimal required permissions for tokens
4. **Image Scanning**: Trivy scans for vulnerabilities automatically

## Best Practices

1. **Version Management**: Use semantic versioning (v1.0.0, v1.0.1, etc.)
2. **Testing**: Ensure all tests pass before merging to main
3. **Monitoring**: Check deployment logs after each deployment
4. **Rollback**: Keep previous image versions for quick rollback
5. **Documentation**: Update this guide as pipeline evolves

## Support

If you encounter issues:

1. Check the GitHub Actions logs for detailed error messages
2. Verify all required secrets are configured
3. Test the deployment manually if automated deployment fails
4. Check the troubleshooting section above for common solutions

## Quick Setup Checklist

- [ ] Add `DOCKERHUB_USERNAME` secret
- [ ] Add `DOCKERHUB_TOKEN` secret  
- [ ] Add `KUBE_CONFIG_DATA` secret
- [ ] Add `CODECOV_TOKEN` secret (optional)
- [ ] Verify kubeconfig points to correct cluster
- [ ] Test pipeline with a small change
- [ ] Monitor first deployment
- [ ] Verify application is running correctly 