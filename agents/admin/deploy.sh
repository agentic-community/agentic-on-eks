#!/bin/bash
set -e

# Configuration
ECR_REPOSITORY_NAME="admin-agent"
IMAGE_TAG="latest"
DEPLOYMENT_FILE="k8s/admin-agent-deploy.yaml"

# Set the directory to the Admin agent directory
ADMIN_DIR="$(dirname "$0")"
cd "$ADMIN_DIR"
echo "Working in directory: $ADMIN_DIR"
echo `pwd`

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

echo "Using AWS Account: $AWS_ACCOUNT_ID"
echo "Using AWS Region: $AWS_REGION"

# Build Docker image
echo "Building Docker image..."
docker build --platform=linux/amd64 -t $ECR_REPOSITORY_NAME:$IMAGE_TAG .

# Log in to ECR
echo "Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Create ECR repository if it doesn't exist
echo "Ensuring ECR repository exists..."
aws ecr describe-repositories --repository-names $ECR_REPOSITORY_NAME --region $AWS_REGION || \
    aws ecr create-repository --repository-name $ECR_REPOSITORY_NAME --region $AWS_REGION

# Tag and push the image
echo "Tagging and pushing image to ECR..."
docker tag $ECR_REPOSITORY_NAME:$IMAGE_TAG $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY_NAME:$IMAGE_TAG
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY_NAME:$IMAGE_TAG

# OAuth credentials for Admin Agent A2A communication
echo "OAuth Configuration for Admin Agent (All-Agents-App):"
echo "Please provide OAuth credentials for Admin Agent A2A communication:"
echo

read -p "OKTA Domain (e.g., trial-3491228.okta.com): " OKTA_DOMAIN
read -p "OKTA Auth Server ID: " OKTA_AUTH_SERVER_ID
read -p "OKTA Client ID: " OKTA_CLIENT_ID
read -s -p "OKTA Client Secret: " OKTA_CLIENT_SECRET
echo

# Validate OAuth inputs
if [[ -z "$OKTA_DOMAIN" || -z "$OKTA_AUTH_SERVER_ID" || -z "$OKTA_CLIENT_ID" || -z "$OKTA_CLIENT_SECRET" ]]; then
    echo "Error: All OAuth credentials are required for Admin Agent A2A communication"
    exit 1
fi

echo "OAuth credentials provided successfully"

# Apply OAuth secrets and ConfigMap
echo "Applying OAuth secrets and configuration..."
sed -e "s|\${OKTA_DOMAIN}|$OKTA_DOMAIN|g" \
    -e "s|\${OKTA_AUTH_SERVER_ID}|$OKTA_AUTH_SERVER_ID|g" \
    -e "s|\${OKTA_CLIENT_ID}|$OKTA_CLIENT_ID|g" \
    -e "s|\${OKTA_CLIENT_SECRET}|$OKTA_CLIENT_SECRET|g" \
    "k8s/admin-agent-oauth-secrets.yaml" | kubectl apply -f -

echo "OAuth secrets applied successfully"

# Prepare Kubernetes deployment file with proper values and apply
echo "Preparing and applying Kubernetes deployment..."
sed -e "s/\${AWS_ACCOUNT_ID}/$AWS_ACCOUNT_ID/g" \
    -e "s/\${AWS_REGION}/$AWS_REGION/g" \
    "$DEPLOYMENT_FILE" | kubectl apply -f -

echo "Deployment completed successfully!"
echo "You can check the status of your deployment with:"
echo "  kubectl get pods -l app=admin-agent"
echo "  kubectl get svc admin-agent-service"
echo ""
echo "To test the Admin agent:"
echo "  kubectl port-forward svc/admin-agent-service 8080:8080"
echo "  curl http://localhost:8080/.well-known/agent.json"