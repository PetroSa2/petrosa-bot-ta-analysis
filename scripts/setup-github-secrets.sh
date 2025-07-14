#!/bin/bash

# GitHub Actions Secrets Setup Script
# This script helps generate the required secrets for the TA Bot CI/CD pipeline

set -e

echo "🔧 GitHub Actions Secrets Setup for TA Bot"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if kubeconfig exists
if [ ! -f "k8s/kubeconfig.yaml" ]; then
    print_error "kubeconfig.yaml not found in k8s/ directory"
    echo "Please ensure your kubeconfig file is in the correct location"
    exit 1
fi

print_info "Generating GitHub Actions secrets..."
echo ""

# 1. Generate KUBE_CONFIG_DATA
print_info "1. Generating KUBE_CONFIG_DATA secret..."
KUBE_CONFIG_DATA=$(cat k8s/kubeconfig.yaml | base64 -w 0)
if [ $? -eq 0 ]; then
    print_status "KUBE_CONFIG_DATA generated successfully"
    echo "Add this to GitHub Secrets as 'KUBE_CONFIG_DATA':"
    echo ""
    echo "$KUBE_CONFIG_DATA"
    echo ""
else
    print_error "Failed to generate KUBE_CONFIG_DATA"
    exit 1
fi

echo ""

# 2. Docker Hub credentials
print_info "2. Docker Hub Credentials"
print_warning "You need to manually create these secrets:"
echo ""
echo "DOCKERHUB_USERNAME: Your Docker Hub username"
echo "DOCKERHUB_TOKEN: Your Docker Hub access token"
echo ""
print_info "To create a Docker Hub token:"
echo "1. Log in to Docker Hub"
echo "2. Go to Account Settings → Security"
echo "3. Click 'New Access Token'"
echo "4. Give it a name (e.g., 'GitHub Actions')"
echo "5. Copy the token and add it to GitHub secrets"
echo ""

# 3. Optional Codecov token
print_info "3. Optional: CODECOV_TOKEN"
print_warning "This is optional for code coverage reporting"
echo "If you want code coverage reporting, add your Codecov token"
echo ""

# 4. Instructions for adding secrets
print_info "4. Adding Secrets to GitHub"
echo ""
echo "To add these secrets to your GitHub repository:"
echo "1. Go to your GitHub repository"
echo "2. Click Settings → Secrets and variables → Actions"
echo "3. Click 'New repository secret'"
echo "4. Add each secret with the exact names shown above"
echo ""

# 5. Test the configuration
print_info "5. Testing Configuration"
echo ""
echo "To test your configuration:"
echo "1. Add all required secrets to GitHub"
echo "2. Make a small change to trigger the pipeline"
echo "3. Check the Actions tab to monitor the workflow"
echo ""

# 6. Verification commands
print_info "6. Verification Commands"
echo ""
echo "After setting up secrets, you can verify:"
echo ""
echo "# Test Kubernetes connection:"
echo "export KUBECONFIG=k8s/kubeconfig.yaml"
echo "kubectl cluster-info --insecure-skip-tls-verify"
echo ""
echo "# Test Docker Hub access (if you have credentials):"
echo "docker login -u YOUR_USERNAME -p YOUR_TOKEN"
echo ""

# 7. Troubleshooting
print_info "7. Troubleshooting"
echo ""
echo "Common issues and solutions:"
echo ""
echo "❌ Docker Hub authentication failed:"
echo "   - Verify DOCKERHUB_USERNAME and DOCKERHUB_TOKEN are correct"
echo "   - Ensure the token has write permissions"
echo ""
echo "❌ Kubernetes connection failed:"
echo "   - Verify KUBE_CONFIG_DATA is properly base64-encoded"
echo "   - Check that the cluster is accessible"
echo ""
echo "❌ Pipeline not triggering:"
echo "   - Ensure you're pushing to main or develop branch"
echo "   - Check that the workflow files are in .github/workflows/"
echo ""

print_status "Setup script completed!"
echo ""
print_info "Next steps:"
echo "1. Add the secrets to your GitHub repository"
echo "2. Test the pipeline with a small change"
echo "3. Monitor the deployment in the Actions tab"
echo "4. Check the deployment status in your MicroK8s cluster"
echo ""

print_warning "Remember: Never commit secrets to your repository!"
echo "All sensitive data should be stored as GitHub secrets." 