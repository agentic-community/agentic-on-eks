#!/bin/bash
set -e

# Helm deployment script for Agentic Platform
# This script provides an easy way to deploy the platform using Helm

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHARTS_DIR="$SCRIPT_DIR/charts"
ENVIRONMENTS_DIR="$SCRIPT_DIR/environments"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Default values
RELEASE_NAME="agents"
MODE="demo"
NAMESPACE="default"
ACTION="install"

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

Deploy the Agentic Platform using Helm charts.

OPTIONS:
    -m, --mode MODE          Deployment mode (demo, secure) [default: demo]
    -n, --namespace NS       Kubernetes namespace [default: default]
    -r, --release RELEASE    Helm release name [default: agents]
    -a, --action ACTION      Action to perform (install, upgrade, uninstall, status) [default: install]
    -h, --help              Show this help message

EXAMPLES:
    # Deploy in demo mode (no OKTA)
    $0 -m demo

    # Deploy to production with OKTA
    $0 -m prod -n production

    # Upgrade existing deployment
    $0 -m prod -a upgrade

    # Check deployment status
    $0 -a status

    # Uninstall deployment
    $0 -a uninstall

PREREQUISITES:
    1. EKS cluster deployed via Terraform
    2. kubectl configured to access the cluster
    3. Helm 3.8+ installed
    4. Demo values file configured in environments/demo-values.yaml (for demo mode)
    5. Environment variables set (see ENVIRONMENT VARIABLES section)

ENVIRONMENT VARIABLES:
    Required for all deployments:
      ACCOUNT_ID - AWS Account ID
    
    Required for secure mode only:
      OKTA_DOMAIN - Your Okta domain
      OKTA_AUTH_SERVER_ID - Okta Auth Server ID
      OKTA_ADMIN_CLIENT_ID - Admin agent OAuth client ID
      OKTA_ADMIN_CLIENT_SECRET - Admin agent OAuth client secret
      OKTA_UI_CLIENT_ID - UI OAuth client ID
      OKTA_UI_CLIENT_SECRET - UI OAuth client secret
      OKTA_REDIRECT_URI - OAuth redirect URI (optional, defaults to localhost)

EOF
}

# Function to validate prerequisites
validate_prerequisites() {
    print_info "Validating prerequisites..."
    
    # Check if kubectl is available and can connect to cluster
    if ! kubectl cluster-info >/dev/null 2>&1; then
        print_error "kubectl cannot connect to Kubernetes cluster. Please configure kubectl."
        exit 1
    fi
    
    # Check if Helm is available
    if ! command -v helm >/dev/null 2>&1; then
        print_error "Helm is not installed. Please install Helm 3.8 or later."
        exit 1
    fi
    
    # Check Helm version
    HELM_VERSION=$(helm version --short --client | grep -oE 'v[0-9]+\.[0-9]+' | sed 's/v//')
    HELM_MAJOR=$(echo $HELM_VERSION | cut -d. -f1)
    HELM_MINOR=$(echo $HELM_VERSION | cut -d. -f2)
    
    if [ "$HELM_MAJOR" -lt 3 ] || ([ "$HELM_MAJOR" -eq 3 ] && [ "$HELM_MINOR" -lt 8 ]); then
        print_error "Helm version $HELM_VERSION found. Please install Helm 3.8 or later."
        exit 1
    fi
    
    # Check if values file exists
    if [ "$ACTION" != "uninstall" ] && [ "$ACTION" != "status" ]; then
        # Check for required files based on mode
        if [ "$MODE" = "demo" ]; then
            DEMO_VALUES_FILE="$ENVIRONMENTS_DIR/demo-values.yaml"
            if [ ! -f "$DEMO_VALUES_FILE" ]; then
                print_error "Demo values file not found: $DEMO_VALUES_FILE"
                exit 1
            fi
        fi
    fi
    
    # Validate required environment variables
    if [ "$ACTION" != "uninstall" ] && [ "$ACTION" != "status" ]; then
        print_info "Validating environment variables..."
        
        # ACCOUNT_ID is always required
        if [ -z "$ACCOUNT_ID" ]; then
            print_error "ACCOUNT_ID environment variable is required"
            print_info "Set it with: export ACCOUNT_ID=\$(aws sts get-caller-identity --query Account --output text)"
            exit 1
        fi
        
        # OKTA variables only required for secure mode
        if [ "$MODE" = "secure" ]; then
            local missing_vars=()
            
            [ -z "$OKTA_DOMAIN" ] && missing_vars+=("OKTA_DOMAIN")
            [ -z "$OKTA_AUTH_SERVER_ID" ] && missing_vars+=("OKTA_AUTH_SERVER_ID")
            [ -z "$OKTA_ADMIN_CLIENT_ID" ] && missing_vars+=("OKTA_ADMIN_CLIENT_ID")
            [ -z "$OKTA_ADMIN_CLIENT_SECRET" ] && missing_vars+=("OKTA_ADMIN_CLIENT_SECRET")
            [ -z "$OKTA_UI_CLIENT_ID" ] && missing_vars+=("OKTA_UI_CLIENT_ID")
            [ -z "$OKTA_UI_CLIENT_SECRET" ] && missing_vars+=("OKTA_UI_CLIENT_SECRET")
            
            if [ ${#missing_vars[@]} -gt 0 ]; then
                print_error "Missing required environment variables for secure mode:"
                for var in "${missing_vars[@]}"; do
                    echo "  - $var"
                done
                print_info "Set these variables before deploying in secure mode"
                exit 1
            fi
        fi
        
        print_success "Environment variables validated"
    fi
    
    print_success "Prerequisites validated"
}

# Function to update Helm dependencies
update_dependencies() {
    print_info "Updating Helm chart dependencies..."
    cd "$CHARTS_DIR/agents"
    helm dependency update
    cd "$SCRIPT_DIR"
    print_success "Dependencies updated"
}

# Function to check if LangFuse is enabled in Terraform
check_langfuse_enabled() {
    # Check if LangFuse secret exists (indicates LangFuse is deployed)
    if kubectl get secret langfuse-credentials -n default >/dev/null 2>&1; then
        return 0  # LangFuse is enabled
    else
        return 1  # LangFuse is not enabled
    fi
}

# Function to install/upgrade the platform
deploy_platform() {
    local helm_action="$1"
    # For secure mode, we don't need a separate values file since base chart has secure defaults
    # For demo mode, we'll use the demo-values.yaml override
    
    print_info "Deploying Agentic Platform..."
    print_info "  Mode: $MODE"
    print_info "  Release: $RELEASE_NAME"
    print_info "  Namespace: $NAMESPACE"
    print_info "  Action: $helm_action"
    
    # Create namespace if it doesn't exist
    if [ "$NAMESPACE" != "default" ]; then
        kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
    fi
    
    # Check if LangFuse is enabled
    local langfuse_values_args=""
    if check_langfuse_enabled; then
        print_info "LangFuse observability detected - enabling LangFuse integration"
        langfuse_values_args="--values $ENVIRONMENTS_DIR/langfuse-values.yaml"
    else
        print_info "LangFuse not detected - deploying without observability"
    fi
    
    # Deploy using Helm based on mode
    if [ "$MODE" = "demo" ]; then
        # For demo mode, use the demo-values.yaml override
        local demo_values_file="$ENVIRONMENTS_DIR/demo-values.yaml"
        if [ -f "$demo_values_file" ]; then
            print_info "Deploying in demo mode (no authentication)"
            helm $helm_action "$RELEASE_NAME" "$CHARTS_DIR/agents" \
                --values "$demo_values_file" \
                $langfuse_values_args \
                --namespace "$NAMESPACE" \
                --set global.aws.accountId="$ACCOUNT_ID" \
                --wait \
                --timeout 10m
        else
            print_error "Demo values file not found: $demo_values_file"
            exit 1
        fi
    else
        # For secure mode, use base chart values with environment variable overrides
        print_info "Deploying in secure mode (with OKTA authentication)"
        
        # Create a temporary values file with environment variables
        local temp_values_file="/tmp/secure-values-${RELEASE_NAME}-$(date +%s).yaml"
        
        cat > "$temp_values_file" <<EOF
# Override values for secure mode deployment
global:
  aws:
    accountId: "$ACCOUNT_ID"

okta:
  domain: "$OKTA_DOMAIN"
  authServerId: "$OKTA_AUTH_SERVER_ID"
  adminAgent:
    clientId: "$OKTA_ADMIN_CLIENT_ID"
    clientSecret: "$OKTA_ADMIN_CLIENT_SECRET"
  ui:
    clientId: "$OKTA_UI_CLIENT_ID"
    clientSecret: "$OKTA_UI_CLIENT_SECRET"
    redirectUri: "${OKTA_REDIRECT_URI:-http://localhost:8501}"
EOF
        
        helm $helm_action "$RELEASE_NAME" "$CHARTS_DIR/agents" \
            --values "$temp_values_file" \
            $langfuse_values_args \
            --namespace "$NAMESPACE" \
            --wait \
            --timeout 10m
        
        # Clean up temp file
        rm -f "$temp_values_file"
    fi
    
    print_success "Platform deployed successfully"
    
    # Show status
    show_status
}

# Function to show deployment status
show_status() {
    print_info "Deployment Status:"
    echo
    
    # Helm status
    echo "=== Helm Release Status ==="
    helm status "$RELEASE_NAME" --namespace "$NAMESPACE" || true
    echo
    
    # Pod status
    echo "=== Pod Status ==="
    kubectl get pods -l "app.kubernetes.io/instance=$RELEASE_NAME" -n "$NAMESPACE" || true
    echo
    
    # Service status
    echo "=== Service Status ==="
    kubectl get svc -l "app.kubernetes.io/instance=$RELEASE_NAME" -n "$NAMESPACE" || true
    echo
    
    # Access instructions
    echo "=== Access Instructions ==="
    if kubectl get svc "${RELEASE_NAME}-ui-app-service" -n "$NAMESPACE" >/dev/null 2>&1; then
        echo "To access the UI application:"
        echo "  kubectl port-forward svc/${RELEASE_NAME}-ui-app-service 8501:80 -n $NAMESPACE"
        echo "  Then open: http://localhost:8501"
    else
        echo "UI service not found or not ready yet."
    fi
}

# Function to uninstall the platform
uninstall_platform() {
    print_warning "Uninstalling Agentic Platform..."
    print_warning "  Release: $RELEASE_NAME"
    print_warning "  Namespace: $NAMESPACE"
    
    read -p "Are you sure you want to uninstall? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        helm uninstall "$RELEASE_NAME" --namespace "$NAMESPACE"
        print_success "Platform uninstalled successfully"
    else
        print_info "Uninstall cancelled"
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--mode)
            MODE="$2"
            shift 2
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -r|--release)
            RELEASE_NAME="$2"
            shift 2
            ;;
        -a|--action)
            ACTION="$2"
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

# Main execution
main() {
    print_info "Starting Agentic Platform Helm deployment script"
    
    case $ACTION in
        install)
            validate_prerequisites
            update_dependencies
            deploy_platform "upgrade --install"
            ;;
        upgrade)
            validate_prerequisites
            update_dependencies
            deploy_platform "upgrade"
            ;;
        uninstall)
            validate_prerequisites
            uninstall_platform
            ;;
        status)
            validate_prerequisites
            show_status
            ;;
        *)
            print_error "Unknown action: $ACTION"
            print_info "Valid actions: install, upgrade, uninstall, status"
            exit 1
            ;;
    esac
}

# Run main function
main