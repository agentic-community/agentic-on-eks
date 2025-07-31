#!/bin/bash
set -e

# Configuration
ECR_REPOSITORY_NAME="hr-agent"
IMAGE_TAG="latest"
DEPLOYMENT_FILE="k8s/hr-agent-deploy.yaml"
# RESOLVED_DEPLOYMENT_FILE="k8s/hr-agent-deploy-resolved.yaml" # This file is no longer generated

# Set the directory to the HR agent directory
HR_DIR="$(dirname "$0")"
cd "$HR_DIR"
echo "Working in directory: $HR_DIR"
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

# No longer need to copy common directory - using latest A2A SDK

# Copy common OAuth utilities for Docker build
echo "Copying common OAuth utilities..."
cp -r ../../common ./common

# Build Docker image
echo "Building Docker image..."
docker build --platform=linux/amd64 -t $ECR_REPOSITORY_NAME:$IMAGE_TAG .

# Clean up common directory after build
rm -rf ./common

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

# [OKTA] Skipped loading Okta environment variables
# if [ -f "../../.okta.env" ]; then
#     echo "Loading Okta environment variables from .okta.env..."
#     source ../../.okta.env
#     echo "Loaded Okta environment variables successfully"
# fi

# Escape slashes in variables for sed
# [OKTA] Skipped escaping Okta variables for sed
# ESCAPED_OKTA_AUDIENCE=$(echo "$OKTA_AUDIENCE" | sed 's/\//\\\//g')
# ESCAPED_OKTA_ISSUER=$(echo "$OKTA_ISSUER" | sed 's/\//\\\//g')
# ESCAPED_OKTA_JWKS_URL=$(echo "$OKTA_JWKS_URL" | sed 's/\//\\\//g')
# ESCAPED_HR_SCOPES=$(echo "$HR_SCOPES" | sed 's/\//\\\//g')

# Prepare Kubernetes deployment file with proper values and apply
echo "Preparing and applying Kubernetes deployment..."
sed -e "s/\${AWS_ACCOUNT_ID}/$AWS_ACCOUNT_ID/g" \
    -e "s/\${AWS_REGION}/$AWS_REGION/g" \
    "$DEPLOYMENT_FILE" | kubectl apply -f -

# Apply OAuth secrets for HR agent
echo "Applying OAuth secrets for HR agent..."
echo "Please provide OAuth configuration for HR agent token validation:"
read -p "OKTA Domain (e.g., trial-3491228.okta.com): " OKTA_DOMAIN
read -p "OKTA Auth Server ID: " OKTA_AUTH_SERVER_ID

# Validate inputs
if [[ -z "$OKTA_DOMAIN" || -z "$OKTA_AUTH_SERVER_ID" ]]; then
    echo "Error: OAuth configuration is required for HR agent token validation"
    exit 1
fi

echo "Applying OAuth secrets for HR agent..."
sed -e "s|\${OKTA_DOMAIN}|$OKTA_DOMAIN|g" \
    -e "s|\${OKTA_AUTH_SERVER_ID}|$OKTA_AUTH_SERVER_ID|g" \
    "k8s/hr-agent-oauth-secrets.yaml" | kubectl apply -f -

echo "Deployment completed successfully!"
echo "You can check the status of your deployment with:"
echo "  kubectl get pods -l app=hr-agent"
echo "  kubectl get svc hr-agent-service"
# echo "  kubectl get ingress hr-agent-ingress" # Ingress removed

# Clean up completed - no common directory to remove
