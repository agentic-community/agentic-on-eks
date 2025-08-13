#!/bin/bash

# deploy-monitoring.sh - Automated LangSmith Monitoring Setup for Agentic-on-EKS
# This script automates the setup of LangSmith Cloud monitoring for all agents

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Function to check if kubectl is available
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed or not in PATH"
        print_error "Please install kubectl and ensure it's configured for your cluster"
        exit 1
    fi
    
    # Check if kubectl can connect to cluster
    if ! kubectl cluster-info &> /dev/null; then
        print_error "kubectl cannot connect to cluster"
        print_error "Please ensure your kubeconfig is properly configured"
        exit 1
    fi
    
    print_success "kubectl is available and connected to cluster"
}

# Function to check if required deployments exist
check_deployments() {
    local deployments=(
        "agents-admin-agent"
        "agents-finance-agent"
        "agents-hr-agent"
    )
    
    print_status "Checking if required deployments exist..."
    
    for deployment in "${deployments[@]}"; do
        if kubectl get deployment "$deployment" &> /dev/null; then
            print_success "Found deployment: $deployment"
        else
            print_error "Deployment not found: $deployment"
            print_error "Please ensure all agents are deployed before running this script"
            exit 1
        fi
    done
}

# Function to get LangSmith API key from user
get_langsmith_api_key() {
    echo
    print_status "LangSmith API Key Setup"
    echo "=================================="
    echo
    echo "To get your LangSmith API key:"
    echo "1. Go to https://smith.langchain.com/"
    echo "2. Sign up/Sign in to your account"
    echo "3. Navigate to your project settings"
    echo "4. Copy your API key (starts with 'ls_...')"
    echo
    echo "Note: If you don't have an API key yet, you can:"
    echo "- Press Enter to skip and set up later"
    echo "- Or provide your API key now"
    echo
    
    echo -n "Enter your LangSmith API key (or press Enter to skip): "
    read LANGCHAIN_API_KEY
    
    echo "DEBUG: Captured API key length: ${#LANGCHAIN_API_KEY}"
    echo "DEBUG: First 20 chars: ${LANGCHAIN_API_KEY:0:20}"
    
    if [[ -z "$LANGCHAIN_API_KEY" ]]; then
        print_warning "No API key provided. You'll need to set it manually later."
        print_warning "Run this script again with your API key when ready."
        return 1
    fi
    
    # Validate API key format
    if [[ ! "$LANGCHAIN_API_KEY" =~ ^ls[a-z0-9_]+_[a-zA-Z0-9_]+$ ]]; then
        print_error "Invalid API key format. LangSmith API keys should start with 'ls' followed by version and underscore"
        print_error "Examples: ls_..., lsv2_..., lsv3_..."
        return 1
    fi
    
    print_success "API key format validated"
    return 0
}

# Function to deploy LangSmith monitoring
deploy_langsmith_monitoring() {
    local api_key="$1"
    
    print_status "Deploying LangSmith monitoring to all agents..."
    
    # Define all deployments
    local deployments=(
        "agents-admin-agent"
        "agents-finance-agent"
        "agents-hr-agent"
    )
    
    # Environment variables to set
    local env_vars=(
        "LANGCHAIN_TRACING_V2=true"
        "LANGCHAIN_ENDPOINT=https://api.smith.langchain.com"
        "LANGCHAIN_API_KEY=$api_key"
        "LANGCHAIN_PROJECT=agentic-on-eks"
        "LANGCHAIN_TRACING=true"
    )
    
    for deployment in "${deployments[@]}"; do
        print_status "Updating $deployment..."
        
        # Set each environment variable
        for env_var in "${env_vars[@]}"; do
            local key="${env_var%%=*}"
            local value="${env_var#*=}"
            
            if kubectl set env deployment/"$deployment" "$key=$value" &> /dev/null; then
                print_success "Set $key for $deployment"
            else
                print_error "Failed to set $key for $deployment"
                return 1
            fi
        done
        
        print_success "Updated $deployment with LangSmith monitoring"
    done
}

# Function to verify monitoring setup
verify_monitoring_setup() {
    print_status "Verifying monitoring setup..."
    
    local deployments=(
        "agents-admin-agent"
        "agents-finance-agent"
        "agents-hr-agent"
    )
    
    for deployment in "${deployments[@]}"; do
        print_status "Checking $deployment environment variables..."
        
        # Check if all required env vars are set
        local required_vars=(
            "LANGCHAIN_TRACING_V2"
            "LANGCHAIN_ENDPOINT"
            "LANGCHAIN_API_KEY"
            "LANGCHAIN_PROJECT"
            "LANGCHAIN_TRACING"
        )
        
        local missing_vars=()
        
        for var in "${required_vars[@]}"; do
            if ! kubectl get deployment "$deployment" -o jsonpath="{.spec.template.spec.containers[0].env[?(@.name=='$var')]}" | grep -q .; then
                missing_vars+=("$var")
            fi
        done
        
        if [[ ${#missing_vars[@]} -eq 0 ]]; then
            print_success "$deployment has all required environment variables"
        else
            print_error "$deployment is missing: ${missing_vars[*]}"
            return 1
        fi
    done
    
    return 0
}

# Function to restart deployments to pick up new environment variables
restart_deployments() {
    print_status "Restarting deployments to apply new environment variables..."
    
    local deployments=(
        "agents-admin-agent"
        "agents-finance-agent"
        "agents-hr-agent"
    )
    
    for deployment in "${deployments[@]}"; do
        print_status "Restarting $deployment..."
        
        if kubectl rollout restart deployment/"$deployment" &> /dev/null; then
            print_success "Restarted $deployment"
        else
            print_error "Failed to restart $deployment"
            return 1
        fi
    done
    
    print_status "Waiting for deployments to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/agents-admin-agent
    kubectl wait --for=condition=available --timeout=300s deployment/agents-finance-agent
    kubectl wait --for=condition=available --timeout=300s deployment/agents-hr-agent
    
    print_success "All deployments are ready"
}

# Function to test LangSmith connectivity
test_langsmith_connectivity() {
    local api_key="$1"
    
    if [[ -z "$api_key" ]]; then
        print_warning "Skipping connectivity test (no API key provided)"
        return 0
    fi
    
    print_status "Testing LangSmith connectivity..."
    
    # Test with a simple API call
    local response
    if response=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $api_key" "https://api.smith.langchain.com/traces" 2>/dev/null); then
        local http_code="${response: -3}"
        local body="${response%???}"
        
        if [[ "$http_code" == "200" ]]; then
            print_success "LangSmith API connectivity test passed"
        else
            print_warning "LangSmith API returned HTTP $http_code"
            print_warning "Response: $body"
        fi
    else
        print_warning "Could not test LangSmith connectivity (curl not available or network issue)"
    fi
}

# Function to show next steps
show_next_steps() {
    local api_key="$1"
    
    echo
    print_success "🎉 LangSmith Monitoring Setup Complete!"
    echo "=============================================="
    echo
    
    if [[ -n "$api_key" ]]; then
        print_success "✅ All agents are now configured with LangSmith monitoring"
        print_success "✅ Environment variables have been set"
        print_success "✅ Deployments have been restarted"
        echo
        echo "🚀 Next Steps:"
        echo "1. Go to https://smith.langchain.com/"
        echo "2. Select your project: 'agentic-on-eks'"
        echo "3. Start using your agents to see traces appear"
        echo "4. Monitor performance and debug issues in real-time"
        echo
        echo "📊 You should see traces appearing within minutes of agent usage"
    else
        print_warning "⚠️  Setup incomplete - API key not provided"
        echo
        echo "🔧 To complete setup:"
        echo "1. Get your LangSmith API key from https://smith.langchain.com/"
        echo "2. Run this script again with your API key"
        echo "3. Or manually set environment variables using kubectl"
        echo
        echo "📖 See README.md for manual setup instructions"
    fi
    
    echo
    echo "🔍 Troubleshooting:"
    echo "- Check agent logs: kubectl logs deployment/agents-admin-agent"
echo "- Verify env vars: kubectl get deployment agents-admin-agent -o yaml | grep -A 10 env:"
    echo "- Monitor traces: https://smith.langchain.com/"
    echo
}

# Function to show help
show_help() {
    echo "🚀 LangSmith Monitoring Setup for Agentic-on-EKS"
    echo "================================================"
    echo
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  --dry-run      Show what would be done without making changes"
    echo
    echo "This script automates the setup of LangSmith Cloud monitoring for all agents."
    echo "It will:"
    echo "  • Check prerequisites (kubectl, deployments)"
    echo "  • Prompt for your LangSmith API key"
    echo "  • Configure all agents with monitoring"
    echo "  • Restart deployments to apply changes"
    echo "  • Verify the setup and test connectivity"
    echo
    echo "Example:"
    echo "  $0                    # Interactive setup"
    echo "  $0 --help            # Show this help"
    echo
    echo "For more information, see README.md"
}

# Function to check command line arguments
check_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            --dry-run)
                print_warning "Dry-run mode not implemented yet"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Main execution
main() {
    # Check command line arguments first
    check_args "$@"
    
    echo "🚀 LangSmith Monitoring Setup for Agentic-on-EKS"
    echo "================================================"
    echo
    
    # Check prerequisites
    check_kubectl
    check_deployments
    
    # Get API key from user
    local api_key=""
    if get_langsmith_api_key; then
        api_key="$LANGCHAIN_API_KEY"
        print_success "Using API key: ${api_key:0:20}..."
    fi
    
    # Deploy monitoring if API key provided
    if [[ -n "$api_key" ]]; then
        deploy_langsmith_monitoring "$api_key"
        
        if verify_monitoring_setup; then
            restart_deployments
            test_langsmith_connectivity "$api_key"
        else
            print_error "Monitoring setup verification failed"
            exit 1
        fi
    fi
    
    # Show next steps
    show_next_steps "$api_key"
}

# Run main function
main "$@"
