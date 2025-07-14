# GitHub Actions Setup for TA Bot

This document explains how to set up automatic versioning and deployment for the TA Bot using GitHub Actions.

## Overview

The GitHub Actions workflow provides:
- **Automatic version incrementing** based on git tags
- **Multi-architecture Docker builds** (linux/amd64, linux/arm64)
- **Security scanning** with Trivy
- **Comprehensive testing** with coverage reporting
- **Kubernetes deployment** to MicroK8s cluster
- **Version tagging** and release management

## Required Secrets

Add these secrets to your GitHub repository (Settings → Secrets and variables → Actions):

### Docker Hub
- `DOCKERHUB_USERNAME`: Your Docker Hub username
- `DOCKERHUB_TOKEN`: Your Docker Hub access token

### Kubernetes
- `KUBE_CONFIG_DATA`: Base64-encoded kubeconfig for MicroK8s cluster
  ```bash
  # Generate this from your kubeconfig.yaml
  cat k8s/kubeconfig.yaml | base64 -w 0
  ```

### Code Coverage (Optional)
- `CODECOV_TOKEN`: Codecov token for coverage reporting

## Workflow Features

### 1. Automatic Versioning
- Uses semantic versioning (v1.0.0, v1.0.1, etc.)
- Automatically increments patch version on each deployment
- Creates and pushes git tags
- Updates Docker image tags and Kubernetes manifests

### 2. Pipeline Stages
1. **Lint and Test**: Code quality checks and unit tests
2. **Security Scan**: Vulnerability scanning with Trivy
3. **Create Release**: Generate version and create git tag
4. **Build and Push**: Multi-arch Docker image build
5. **Deploy**: Kubernetes deployment to MicroK8s
6. **Notify**: Deployment status notifications

### 3. Version Management
- Version is automatically incremented from latest git tag
- If no tags exist, starts at v1.0.0
- Version is embedded in Docker image and health endpoint
- Kubernetes manifests are updated with versioned image tags

## Usage

### Automatic Deployment
- Push to `main` branch triggers automatic deployment
- Push to `develop` branch runs tests but doesn't deploy
- Create git tags manually for specific releases

### Manual Deployment
```bash
# Create a specific version tag
git tag v1.2.3
git push origin v1.2.3
```

### Monitoring Deployment
```bash
# Check deployment status
kubectl get all -l app=petrosa-ta-bot -n petrosa-apps

# View logs
kubectl logs -l app=petrosa-ta-bot -n petrosa-apps

# Check version
curl http://your-domain/health
```

## Configuration

### Image Name
Update the image name in `.github/workflows/release.yml`:
```yaml
env:
  IMAGE_NAME: ${{ secrets.DOCKERHUB_USERNAME }}/petrosa-ta-bot
```

### Kubernetes Namespace
The workflow deploys to `petrosa-apps` namespace. Update if needed:
```yaml
kubectl apply -f k8s/ --recursive --insecure-skip-tls-verify
```

### Coverage Threshold
Adjust the coverage threshold in the workflow:
```yaml
COVERAGE_THRESHOLD=80
```

## Troubleshooting

### Common Issues

1. **Docker Hub Authentication**
   - Ensure `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` are set
   - Token must have write permissions

2. **Kubernetes Connection**
   - Verify `KUBE_CONFIG_DATA` is correctly base64-encoded
   - Check MicroK8s cluster is accessible

3. **Version Conflicts**
   - Delete conflicting tags: `git tag -d v1.0.1`
   - Push deletion: `git push origin :refs/tags/v1.0.1`

4. **Build Failures**
   - Check Docker Hub rate limits
   - Verify Dockerfile syntax
   - Review build logs for dependency issues

### Debug Commands
```bash
# Check git tags
git tag --sort=-version:refname

# Verify kubeconfig
kubectl cluster-info --insecure-skip-tls-verify

# Check deployment
kubectl get deployment petrosa-ta-bot -n petrosa-apps
```

## Security Considerations

1. **Secrets Management**
   - Never commit secrets to the repository
   - Use GitHub Secrets for sensitive data
   - Rotate tokens regularly

2. **Image Security**
   - Trivy scans for vulnerabilities
   - Multi-stage builds reduce attack surface
   - Non-root user in container

3. **Network Security**
   - Ingress with SSL termination
   - Internal service communication
   - Proper RBAC configuration

## Next Steps

1. **Set up secrets** in GitHub repository
2. **Test the workflow** with a small change
3. **Monitor deployments** and logs
4. **Configure notifications** (Slack, email, etc.)
5. **Set up monitoring** for the deployed application

## Support

For issues with the GitHub Actions workflow:
1. Check the Actions tab in GitHub
2. Review workflow logs for specific errors
3. Verify secrets and permissions
4. Test locally with the local pipeline script 