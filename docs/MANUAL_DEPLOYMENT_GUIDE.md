# Manual Deployment Guide - TA Bot

This guide explains how to manually trigger deployments for TA Bot without requiring code changes.

## Overview

The manual deployment workflow allows you to:
- Deploy without code changes (config-only updates)
- Bump version numbers for tracking
- Re-deploy after infrastructure changes
- Create new Docker images with existing code
- Maintain full audit trail of deployments

## Prerequisites

- Access to PetroSa2 GitHub organization
- Permissions to trigger GitHub Actions workflows
- Kubernetes credentials configured in repository secrets
- Understanding of semantic versioning

## Usage

### Option 1: GitHub UI (Recommended)

1. Navigate to [Actions tab](https://github.com/PetroSa2/petrosa-bot-ta-analysis/actions)
2. Click on "Manual Deployment with Version Bump" workflow
3. Click "Run workflow" button
4. Fill in the parameters:
   - **Environment**: `staging` or `production`
   - **Version bump type**: `patch` (bug fixes), `minor` (features), or `major` (breaking changes)
   - **Reason**: Brief explanation for audit trail (required)
5. Click "Run workflow"

**Example**:
```
Environment: staging
Version bump: patch
Reason: Updated NATS connection settings via ConfigMap
```

### Option 2: GitHub CLI

```bash
# Install GitHub CLI if needed
brew install gh

# Trigger deployment
gh workflow run "Manual Deployment with Version Bump" \
  --repo PetroSa2/petrosa-bot-ta-analysis \
  --ref main \
  -f environment=staging \
  -f version_bump=patch \
  -f reason="Updated environment variables for staging"
```

### Option 3: API Call

```bash
curl -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/repos/PetroSa2/petrosa-bot-ta-analysis/actions/workflows/manual-deploy.yml/dispatches \
  -d '{
    "ref":"main",
    "inputs":{
      "environment":"staging",
      "version_bump":"patch",
      "reason":"Infrastructure update"
    }
  }'
```

## How It Works

The workflow performs the following steps:

1. **Version Bump**: Increments version number based on type
   - `patch`: v1.2.3 → v1.2.4 (bug fixes, minor updates)
   - `minor`: v1.2.3 → v1.3.0 (new features, backward compatible)
   - `major`: v1.2.3 → v2.0.0 (breaking changes)

2. **Git Tag**: Creates annotated tag with deployment reason

3. **Docker Build**: Builds new Docker image with version tag

4. **Registry Push**: Pushes image to GitHub Container Registry:
   - `ghcr.io/petrosa2/ta-bot:v1.2.4` (version-specific)
   - `ghcr.io/petrosa2/ta-bot:latest` (always updated)

5. **Kubernetes Update**: Updates deployment with new image tag

6. **Rollout Wait**: Waits for pods to be ready (5min timeout)

7. **Verification**: Checks pod status and logs

8. **Audit Record**: Creates deployment history log

## Verification

After triggering deployment:

1. **Check workflow status**:
   - Go to Actions tab
   - Click on your workflow run
   - Review step-by-step progress

2. **Verify pod status**:
   ```bash
   kubectl get pods -n petrosa-apps -l app=ta-bot --insecure-skip-tls-verify
   ```

3. **Check logs**:
   ```bash
   kubectl logs -n petrosa-apps -l app=ta-bot --tail=50 --insecure-skip-tls-verify
   ```

4. **Verify version**:
   ```bash
   kubectl describe deployment petrosa-ta-bot -n petrosa-apps --insecure-skip-tls-verify | grep Image
   ```

## Common Use Cases

### 1. Configuration Update

**Scenario**: Updated ConfigMap or Secret, need to restart pods with new config

```
Environment: staging
Version bump: patch
Reason: Updated NATS connection timeout in ConfigMap
```

### 2. Infrastructure Change

**Scenario**: Kubernetes cluster upgraded, need to re-deploy services

```
Environment: production
Version bump: patch
Reason: Re-deployment after cluster upgrade from v1.27 to v1.28
```

### 3. Hotfix Without Code

**Scenario**: Need to adjust resource limits in deployment manifest

```
Environment: production
Version bump: patch
Reason: Increased memory limit from 512Mi to 1Gi
```

### 4. Force Restart

**Scenario**: Service stuck or misbehaving, need fresh pods

```
Environment: staging
Version bump: patch
Reason: Force restart due to memory leak investigation
```

## Rollback

If deployment fails or causes issues:

```bash
# Rollback to previous version
kubectl rollout undo deployment/petrosa-ta-bot -n petrosa-apps --insecure-skip-tls-verify

# Check rollback status
kubectl rollout status deployment/petrosa-ta-bot -n petrosa-apps --insecure-skip-tls-verify

# Verify which version is running
kubectl describe deployment petrosa-ta-bot -n petrosa-apps --insecure-skip-tls-verify | grep Image
```

## Version History

View deployment history:

```bash
# Git tags
git tag -l "v*" --sort=-v:refname

# Tag details
git show v1.2.4

# Deployment logs (if committed)
cat deployments/history.log
```

## Troubleshooting

### Issue: Workflow fails at "Build Docker image"

**Cause**: Docker build error or missing dependencies

**Solution**:
1. Check workflow logs for build errors
2. Verify Dockerfile is valid
3. Ensure all required files are committed

### Issue: Workflow fails at "Deploy to Kubernetes"

**Cause**: kubectl authentication or connection issues

**Solution**:
1. Verify KUBECONFIG secret is up to date
2. Check cluster connectivity
3. Ensure namespace `petrosa-apps` exists

### Issue: Pods not starting after deployment

**Cause**: Image pull errors or resource constraints

**Solution**:
```bash
# Check pod events
kubectl get events -n petrosa-apps --field-selector involvedObject.kind=Pod --insecure-skip-tls-verify

# Check pod status
kubectl describe pod <pod-name> -n petrosa-apps --insecure-skip-tls-verify

# Check image availability
kubectl get pods -n petrosa-apps -l app=ta-bot -o jsonpath='{.items[0].status.containerStatuses[0].state}' --insecure-skip-tls-verify
```

### Issue: Version bump fails

**Cause**: Invalid current version or git tag conflicts

**Solution**:
1. Verify latest git tag format (must be vX.Y.Z)
2. Check for duplicate tags
3. Manually create initial tag if needed:
   ```bash
   git tag -a v0.1.0 -m "Initial version"
   git push origin v0.1.0
   ```

## Security Notes

- Workflow requires `contents: write` permission for git tags
- Workflow requires `packages: write` permission for Docker registry
- KUBECONFIG secret must be base64-encoded
- TLS verification is skipped due to external IP not in certificate SAN
- All deployments are logged for audit trail

## Best Practices

1. **Always provide meaningful reason**: Helps with debugging and audit
2. **Test in staging first**: Verify deployment works before production
3. **Use appropriate bump type**:
   - `patch` for minor fixes and config updates
   - `minor` for new features
   - `major` for breaking changes
4. **Monitor after deployment**: Watch logs and metrics for 5-10 minutes
5. **Keep version history**: Don't delete old tags or deployment logs

## Related Documentation

- [GitHub Actions Workflow Dispatch](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_dispatch)
- [Semantic Versioning](https://semver.org/)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Kubernetes Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)

## Support

For issues or questions:
- Create an issue in the repository
- Check workflow run logs in Actions tab
- Review Kubernetes events and logs
- Contact DevOps team for cluster-level issues
