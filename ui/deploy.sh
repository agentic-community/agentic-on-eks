#!/bin/bash
set -e

# Configuration
ECR_REPOSITORY_NAME="ui-app" # Changed from agent-ui
IMAGE_TAG="latest"
DEPLOYMENT_FILE="k8s/ui-app-deploy.yaml" # Changed from agent-ui-deploy.yaml
SECRETS_FILE="k8s/ui-app-secrets.yaml"

# OKTA Configuration - Prompt user for values if not set as environment variables
if [ -z "$OKTA_DOMAIN" ]; then
    echo -n "Enter OKTA Domain (e.g., trial-3491228.okta.com): "
    read OKTA_DOMAIN
fi

if [ -z "$OKTA_CLIENT_ID" ]; then
    echo -n "Enter OKTA Client ID: "
    read OKTA_CLIENT_ID
fi

if [ -z "$OKTA_CLIENT_SECRET" ]; then
    echo -n "Enter OKTA Client Secret: "
    read -s OKTA_CLIENT_SECRET  # -s flag hides input for security
    echo ""  # Add newline after hidden input
fi

# Export the variables for sed substitution
export OKTA_DOMAIN
export OKTA_CLIENT_ID  
export OKTA_CLIENT_SECRET

# Set the directory to the UI directory
UI_DIR="$(dirname "$0")"
cd "$UI_DIR"
echo "Working in directory: $UI_DIR"

# Get AWS account ID and region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Prompt for AWS region with default
read -p "Enter AWS region (default: us-west-2): " USER_AWS_REGION
AWS_REGION=${USER_AWS_REGION:-"us-west-2"}

if [ -z "$AWS_ACCOUNT_ID" ] || [ -z "$AWS_REGION" ]; then
    echo "Error: AWS_ACCOUNT_ID or AWS_REGION not found"
    echo "Make sure AWS CLI is configured properly"
    exit 1
fi

# OKTA configuration is set with defaults above, no validation needed
echo "OKTA Configuration:"
echo "  Domain: $OKTA_DOMAIN"
echo "  Client ID: $OKTA_CLIENT_ID"
echo "  Client Secret: ${OKTA_CLIENT_SECRET:0:10}..."

echo "Using AWS Account: $AWS_ACCOUNT_ID"
echo "Using AWS Region: $AWS_REGION"

# No longer need to copy common directory - using latest A2A SDK

# Log in to ECR
echo "Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Create ECR repository if it doesn't exist
echo "Ensuring ECR repository $ECR_REPOSITORY_NAME exists..."
aws ecr describe-repositories --repository-names $ECR_REPOSITORY_NAME --region $AWS_REGION || \
    aws ecr create-repository --repository-name $ECR_REPOSITORY_NAME --region $AWS_REGION

# Build and push Docker image for linux/amd64 platform
echo "Building and pushing Docker image $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY_NAME:$IMAGE_TAG for linux/amd64..."
docker buildx build --platform linux/amd64 -t $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY_NAME:$IMAGE_TAG --push .

# Apply OKTA secrets and configuration first
echo "Applying OKTA secrets and configuration..."
echo "Using OKTA Domain: $OKTA_DOMAIN"
echo "Using OKTA Client ID: $OKTA_CLIENT_ID"
echo "Using OKTA Client Secret: ${OKTA_CLIENT_SECRET:0:10}..." # Show only first 10 chars for security

# Use sed to replace OKTA variables in secrets file
sed -e "s|\${OKTA_DOMAIN}|$OKTA_DOMAIN|g" \
    -e "s|\${OKTA_CLIENT_ID}|$OKTA_CLIENT_ID|g" \
    -e "s|\${OKTA_CLIENT_SECRET}|$OKTA_CLIENT_SECRET|g" \
    "$SECRETS_FILE" | kubectl apply -f -

# Wait a moment for secrets to be created
sleep 2

# Prepare Kubernetes deployment file and apply
echo "Preparing and applying Kubernetes deployment..."
sed -e "s|\${AWS_ACCOUNT_ID}|$AWS_ACCOUNT_ID|g" \
    -e "s|\${AWS_REGION}|$AWS_REGION|g" \
    "$DEPLOYMENT_FILE" | kubectl apply -f -

echo "Deployment completed successfully!"

# Wait for deployment to be ready
echo "Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/ui-app-deployment

echo ""
echo "🎉 UI Application deployed successfully with OKTA authentication!"
echo ""
echo "📝 To access the application (using internal LoadBalancer):"
echo "   kubectl port-forward svc/ui-app-service 8501:80"
echo "   Then visit: http://localhost:8501"
echo ""
echo "🔐 OKTA Authentication Configuration:"
echo "   - Domain: trial-3491228.okta.com"
echo "   - Redirect URI: http://localhost:8501 (configured for port-forward access)"
echo "   - Mode: OKTA authentication (secrets-based)"
echo ""
echo "💡 To switch to demo mode:"
echo "   kubectl patch configmap ui-app-config -p '{\"data\":{\"DEMO_MODE\":\"true\"}}'"
echo "   kubectl rollout restart deployment/ui-app-deployment"
echo ""
echo "📋 Current pods and services:"
kubectl get pods -l app=ui-app
kubectl get svc ui-app-service

# Clean up
echo "Cleaning up common directory copy..."
# Clean up completed - no common directory to remove