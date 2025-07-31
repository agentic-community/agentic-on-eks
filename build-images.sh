#!/bin/bash
set -e

# Docker Image Build Script for Agentic Platform
# This script builds and pushes all Docker images to ECR without Kubernetes deployment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_TAG="latest"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
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

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Build and push all Docker images for the Agentic Platform to ECR.

OPTIONS:
    -r, --region REGION     AWS region [default: us-west-2]
    -t, --tag TAG          Image tag [default: latest]
    -h, --help             Show this help message

EXAMPLES:
    # Build all images with default settings
    $0

    # Build with custom region and tag
    $0 -r us-east-1 -t v1.0.0

PREREQUISITES:
    1. AWS CLI configured with appropriate permissions
    2. Docker installed and running
    3. ECR repositories will be created automatically if they don't exist

IMAGES BUILT:
    - admin-agent
    - hr-agent
    - finance-agent
    - ui-app

EOF
}

# Parse command line arguments
AWS_REGION="us-west-2"

while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--region)
            AWS_REGION="$2"
            shift 2
            ;;
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate prerequisites
validate_prerequisites() {
    print_info "Validating prerequisites..."
    
    # Check if AWS CLI is available
    if ! command -v aws >/dev/null 2>&1; then
        print_error "AWS CLI is not installed. Please install AWS CLI."
        exit 1
    fi
    
    # Check if Docker is available
    if ! command -v docker >/dev/null 2>&1; then
        print_error "Docker is not installed. Please install Docker."
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi
    
    # Get AWS account ID
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
    if [ -z "$AWS_ACCOUNT_ID" ]; then
        print_error "Cannot get AWS Account ID. Please configure AWS CLI."
        exit 1
    fi
    
    print_success "Prerequisites validated"
    print_info "AWS Account ID: $AWS_ACCOUNT_ID"
    print_info "AWS Region: $AWS_REGION"
    print_info "Image Tag: $IMAGE_TAG"
}

# Function to login to ECR
ecr_login() {
    print_info "Logging in to ECR..."
    aws ecr get-login-password --region "$AWS_REGION" | \
        docker login --username AWS --password-stdin \
        "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
    print_success "ECR login successful"
}

# Function to ensure ECR repository exists
ensure_ecr_repository() {
    local repo_name="$1"
    print_info "Ensuring ECR repository '$repo_name' exists..."
    
    if ! aws ecr describe-repositories --repository-names "$repo_name" --region "$AWS_REGION" >/dev/null 2>&1; then
        print_info "Creating ECR repository '$repo_name'..."
        aws ecr create-repository --repository-name "$repo_name" --region "$AWS_REGION" >/dev/null
        print_success "ECR repository '$repo_name' created"
    else
        print_info "ECR repository '$repo_name' already exists"
    fi
}

# Function to build and push a single image
build_and_push_image() {
    local component_dir="$1"
    local repo_name="$2"
    local needs_common="$3"
    
    print_info "Building $repo_name image..."
    
    if [ "$needs_common" = "true" ]; then
        # For agents that need common directory, build from root with context
        print_info "Building $repo_name with common dependencies from root context..."
        docker build --platform=linux/amd64 \
            -f "$component_dir/Dockerfile" \
            -t "$repo_name:$IMAGE_TAG" \
            .
    else
        # For components that don't need common, build from their directory
        print_info "Building $repo_name from component directory..."
        cd "$SCRIPT_DIR/$component_dir"
        docker build --platform=linux/amd64 -t "$repo_name:$IMAGE_TAG" .
        cd "$SCRIPT_DIR"
    fi
    
    # Ensure ECR repository exists
    ensure_ecr_repository "$repo_name"
    
    # Tag and push image
    local ecr_uri="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$repo_name:$IMAGE_TAG"
    print_info "Tagging image: $ecr_uri"
    docker tag "$repo_name:$IMAGE_TAG" "$ecr_uri"
    
    print_info "Pushing image to ECR..."
    docker push "$ecr_uri"
    
    print_success "$repo_name image built and pushed successfully"
}

# Main build function
build_all_images() {
    print_info "Starting Docker image build process..."
    
    # Login to ECR once
    ecr_login
    
    # Build all images
    print_info "Building all component images..."
    
    # Admin Agent (no common directory needed)
    build_and_push_image "agents/admin" "admin-agent" "false"
    
    # HR Agent (needs common directory)
    build_and_push_image "agents/hr" "hr-agent" "true"
    
    # Finance Agent (needs common directory)
    build_and_push_image "agents/finance" "finance-agent" "true"
    
    # UI App (no common directory needed)
    build_and_push_image "ui" "ui-app" "false"
    
    print_success "All images built and pushed successfully!"
}

# Function to show build summary
show_summary() {
    print_info "Build Summary:"
    echo
    echo "=== Images Built ==="
    echo "• $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/admin-agent:$IMAGE_TAG"
    echo "• $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/hr-agent:$IMAGE_TAG"
    echo "• $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/finance-agent:$IMAGE_TAG"
    echo "• $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ui-app:$IMAGE_TAG"
    echo
    echo "=== Next Steps ==="
    echo "1. Set required environment variables:"
    echo "   export ACCOUNT_ID=\"$AWS_ACCOUNT_ID\""
    echo
    echo "2. For production mode, also set OKTA variables:"
    echo "   export OKTA_DOMAIN=\"your-domain.okta.com\""
    echo "   export OKTA_AUTH_SERVER_ID=\"your-auth-server-id\""
    echo "   export OKTA_ADMIN_CLIENT_ID=\"your-admin-client-id\""
    echo "   export OKTA_ADMIN_CLIENT_SECRET=\"your-admin-secret\""
    echo "   export OKTA_UI_CLIENT_ID=\"your-ui-client-id\""
    echo "   export OKTA_UI_CLIENT_SECRET=\"your-ui-secret\""
    echo
    echo "3. Deploy using Helm:"
    echo "   ./deploy-helm.sh -m demo    # For demo mode (no OKTA)"
    echo "   ./deploy-helm.sh -m prod    # For production mode (with OKTA)"
    echo
}

# Main execution
main() {
    print_info "Starting Agentic Platform Docker Image Build"
    
    validate_prerequisites
    build_all_images
    show_summary
    
    print_success "Docker image build process completed successfully!"
}

# Run main function
main