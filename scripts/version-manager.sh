#!/bin/bash

# Petrosa TA Bot Version Manager
# Generates auto-incremental versions for local development and deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to generate version
generate_version() {
    local version_type=$1
    
    case $version_type in
        "patch")
            # Get latest version from git tags
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
            ;;
        "minor")
            LATEST_VERSION=$(git tag --sort=-version:refname | grep '^v[0-9]' | head -1)
            if [ -z "$LATEST_VERSION" ]; then
                VERSION="v1.0.0"
            else
                if [[ "$LATEST_VERSION" =~ ^v([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
                    MAJOR="${BASH_REMATCH[1]}"
                    MINOR="${BASH_REMATCH[2]}"
                    NEW_MINOR=$((MINOR + 1))
                    VERSION="v${MAJOR}.${NEW_MINOR}.0"
                else
                    VERSION="v1.0.0"
                fi
            fi
            ;;
        "major")
            LATEST_VERSION=$(git tag --sort=-version:refname | grep '^v[0-9]' | head -1)
            if [ -z "$LATEST_VERSION" ]; then
                VERSION="v1.0.0"
            else
                if [[ "$LATEST_VERSION" =~ ^v([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
                    MAJOR="${BASH_REMATCH[1]}"
                    NEW_MAJOR=$((MAJOR + 1))
                    VERSION="v${NEW_MAJOR}.0.0"
                else
                    VERSION="v1.0.0"
                fi
            fi
            ;;
        "local")
            # Generate local development version with timestamp
            TIMESTAMP=$(date +%Y%m%d-%H%M%S)
            COMMIT_SHA=$(git rev-parse --short HEAD)
            VERSION="local-${TIMESTAMP}-${COMMIT_SHA}"
            ;;
        *)
            print_error "Unknown version type: $version_type"
            print_error "Available types: patch, minor, major, local"
            exit 1
            ;;
    esac
    
    echo "$VERSION"
}

# Function to update Kubernetes manifests
update_k8s_manifests() {
    local version=$1
    local docker_username=${2:-"yurisa2"}
    
    print_status "Updating Kubernetes manifests with version: $version"
    
    # Update deployment.yaml
    if [ -f "k8s/deployment.yaml" ]; then
        sed -i.bak "s|VERSION_PLACEHOLDER|${version}|g" k8s/deployment.yaml
        sed -i.bak "s|yurisa2/petrosa-ta-bot:VERSION_PLACEHOLDER|${docker_username}/petrosa-ta-bot:${version}|g" k8s/deployment.yaml
        rm -f k8s/deployment.yaml.bak
        print_success "Updated k8s/deployment.yaml"
    fi
    
    # Update other manifests if they contain VERSION_PLACEHOLDER
    find k8s/ -name "*.yaml" -exec grep -l "VERSION_PLACEHOLDER" {} \; | while read file; do
        sed -i.bak "s|VERSION_PLACEHOLDER|${version}|g" "$file"
        rm -f "${file}.bak"
        print_success "Updated $file"
    done
}

# Function to build and tag Docker image
build_docker_image() {
    local version=$1
    local docker_username=${2:-"yurisa2"}
    
    print_status "Building Docker image with version: $version"
    
    # Build the image with platform specification for macOS compatibility
    if ! docker build --platform linux/amd64 -t "${docker_username}/petrosa-ta-bot:${version}" .; then
        print_warning "Docker build failed, trying without platform specification..."
        if ! docker build -t "${docker_username}/petrosa-ta-bot:${version}" .; then
            print_error "Docker build failed. Please check your Docker installation."
            return 1
        fi
    fi
    
    docker tag "${docker_username}/petrosa-ta-bot:${version}" "${docker_username}/petrosa-ta-bot:latest"
    
    print_success "Built Docker image: ${docker_username}/petrosa-ta-bot:${version}"
}

# Function to deploy to Kubernetes
deploy_to_k8s() {
    local version=$1
    
    print_status "Deploying to Kubernetes with version: $version"
    
    # Set kubeconfig
    export KUBECONFIG=k8s/kubeconfig.yaml
    
    # Apply manifests
    kubectl apply -f k8s/ --recursive
    
    print_success "Deployed to Kubernetes with version: $version"
}

# Function to create git tag
create_git_tag() {
    local version=$1
    local push_tag=${2:-false}
    
    print_status "Creating git tag: $version"
    
    if git rev-parse "$version" >/dev/null 2>&1; then
        print_warning "Tag $version already exists, deleting and recreating..."
        git tag -d "$version"
        git push origin ":refs/tags/$version" 2>/dev/null || true
    fi
    
    git tag "$version"
    
    if [ "$push_tag" = "true" ]; then
        git push origin "$version"
        print_success "Pushed tag $version to remote"
    else
        print_success "Created local tag $version"
    fi
}

# Main execution
case "${1:-help}" in
    "generate")
        version_type=${2:-"patch"}
        version=$(generate_version "$version_type")
        echo "$version"
        ;;
    "build")
        version_type=${2:-"local"}
        version=$(generate_version "$version_type")
        docker_username=${3:-"yurisa2"}
        
        update_k8s_manifests "$version" "$docker_username"
        build_docker_image "$version" "$docker_username"
        
        print_success "Build completed with version: $version"
        ;;
    "deploy")
        version_type=${2:-"local"}
        version=$(generate_version "$version_type")
        docker_username=${3:-"yurisa2"}
        
        update_k8s_manifests "$version" "$docker_username"
        build_docker_image "$version" "$docker_username"
        deploy_to_k8s "$version"
        
        print_success "Deployment completed with version: $version"
        ;;
    "tag")
        version_type=${2:-"patch"}
        push_tag=${3:-"false"}
        version=$(generate_version "$version_type")
        
        create_git_tag "$version" "$push_tag"
        ;;
    "full")
        version_type=${2:-"patch"}
        push_tag=${3:-"false"}
        docker_username=${4:-"yurisa2"}
        version=$(generate_version "$version_type")
        
        update_k8s_manifests "$version" "$docker_username"
        build_docker_image "$version" "$docker_username"
        deploy_to_k8s "$version"
        create_git_tag "$version" "$push_tag"
        
        print_success "Full pipeline completed with version: $version"
        ;;
    "help"|*)
        echo "Petrosa TA Bot Version Manager"
        echo "============================="
        echo ""
        echo "Usage: $0 <command> [options]"
        echo ""
        echo "Commands:"
        echo "  generate <type>     Generate version (patch|minor|major|local)"
        echo "  build <type> [user] Build Docker image with version"
        echo "  deploy <type> [user] Deploy to Kubernetes with version"
        echo "  tag <type> [push]   Create git tag (push: true|false)"
        echo "  full <type> [push] [user] Run full pipeline"
        echo "  help                Show this help"
        echo ""
        echo "Version Types:"
        echo "  patch               Increment patch version (1.0.0 -> 1.0.1)"
        echo "  minor               Increment minor version (1.0.0 -> 1.1.0)"
        echo "  major               Increment major version (1.0.0 -> 2.0.0)"
        echo "  local               Local development version with timestamp"
        echo ""
        echo "Examples:"
        echo "  $0 generate patch"
        echo "  $0 build local"
        echo "  $0 deploy patch"
        echo "  $0 full patch true"
        ;;
esac 