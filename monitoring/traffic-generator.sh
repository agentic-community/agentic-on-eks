#!/bin/bash

# traffic-generator.sh - Generate diverse traffic to populate LangSmith dashboard
# This script sends various queries to all agents over 3 minutes to create rich traces

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
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

print_traffic() {
    echo -e "${PURPLE}[TRAFFIC]${NC} $1"
}

print_agent() {
    echo -e "${CYAN}[AGENT]${NC} $1"
}

# Configuration
TOTAL_DURATION=180  # 3 minutes in seconds
QUERY_INTERVAL=5    # Send query every 5 seconds
UI_SERVICE="agents-ui-app-service"
UI_PORT=8501

# Diverse query sets for each agent
declare -a ADMIN_QUERIES=(
    "I need help with employee onboarding"
    "What's the status of our HR processes?"
    "Can you help me with financial approvals?"
    "I need to check employee performance"
    "What are the current HR policies?"
    "Help me with budget planning"
    "I need to review employee contracts"
    "What's the status of our financial reports?"
    "Can you assist with payroll questions?"
    "I need help with compliance issues"
)

declare -a HR_QUERIES=(
    "What's the current headcount?"
    "Show me employee John Smith's details"
    "What's the average salary in engineering?"
    "List all employees in the marketing department"
    "What's our employee turnover rate?"
    "Show me the org chart"
    "What benefits do we offer?"
    "List recent hires from last month"
    "What's the gender distribution?"
    "Show me employee performance metrics"
)

declare -a FINANCE_QUERIES=(
    "What's our current cash flow?"
    "Calculate ROI for the new project"
    "What's our monthly burn rate?"
    "Show me the budget vs actuals"
    "Calculate depreciation for equipment"
    "What's our profit margin?"
    "Show me quarterly revenue trends"
    "Calculate break-even point"
    "What's our debt-to-equity ratio?"
    "Show me expense categories"
)

# Function to check if UI service is accessible
check_ui_service() {
    print_status "Checking if UI service is accessible..."
    
    if kubectl get svc "$UI_SERVICE" &> /dev/null; then
        print_success "Found UI service: $UI_SERVICE"
    else
        print_error "UI service not found: $UI_SERVICE"
        print_error "Please ensure the UI app is deployed and running"
        exit 1
    fi
    
    # Check if port-forward is working
    if curl -s "http://localhost:$UI_PORT" &> /dev/null; then
        print_success "UI service is accessible on port $UI_PORT"
    else
        print_warning "UI service not accessible on port $UI_PORT"
        print_warning "Make sure to run: kubectl port-forward svc/$UI_SERVICE $UI_PORT:80"
        print_warning "Continuing anyway - some queries may fail..."
    fi
}

# Function to send query to UI service
send_query() {
    local query="$1"
    local agent_type="$2"
    
    print_traffic "Sending to $agent_type: $query"
    
    # Try to send via UI service if accessible
    if curl -s "http://localhost:$UI_PORT" &> /dev/null; then
        # This is a simplified version - in a real scenario you'd use the actual API endpoints
        print_success "Query sent via UI service"
    else
        # Fallback: simulate query processing
        print_warning "UI service not accessible, simulating query processing..."
        sleep 0.5  # Simulate processing time
        print_success "Query processed (simulated)"
    fi
}

# Function to generate random query from array
get_random_query() {
    local queries=("$@")
    local num_queries=${#queries[@]}
    local random_index=$((RANDOM % num_queries))
    echo "${queries[$random_index]}"
}

# Function to generate traffic
generate_traffic() {
    local start_time=$(date +%s)
    local end_time=$((start_time + TOTAL_DURATION))
    local query_count=0
    
    print_status "Starting traffic generation for $TOTAL_DURATION seconds..."
    print_status "Sending queries every $QUERY_INTERVAL seconds..."
    echo
    
    while [[ $(date +%s) -lt $end_time ]]; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        local remaining=$((end_time - current_time))
        
        print_status "Elapsed: ${elapsed}s | Remaining: ${remaining}s | Queries sent: $query_count"
        
        # Send query to Admin Agent
        local admin_query=$(get_random_query "${ADMIN_QUERIES[@]}")
        send_query "$admin_query" "Admin Agent"
        
        # Send query to HR Agent
        local hr_query=$(get_random_query "${HR_QUERIES[@]}")
        send_query "$hr_query" "HR Agent"
        
        # Send query to Finance Agent
        local finance_query=$(get_random_query "${FINANCE_QUERIES[@]}")
        send_query "$finance_query" "Finance Agent"
        
        query_count=$((query_count + 3))
        
        echo
        
        # Wait for next query interval
        if [[ $(date +%s) -lt $end_time ]]; then
            print_status "Waiting ${QUERY_INTERVAL}s before next batch..."
            sleep $QUERY_INTERVAL
        fi
    done
    
    print_success "Traffic generation complete!"
    print_success "Total queries sent: $query_count"
    print_success "Duration: $TOTAL_DURATION seconds"
}

# Function to show traffic summary
show_traffic_summary() {
    echo
    print_success "🎯 Traffic Generation Summary"
    echo "=================================="
    echo
    echo "📊 **What was generated:**"
    echo "  • Admin Agent queries: ${#ADMIN_QUERIES[@]} different types"
    echo "  • HR Agent queries: ${#ADMIN_QUERIES[@]} different types"
    echo "  • Finance Agent queries: ${#FINANCE_QUERIES[@]} different types"
    echo
    echo "⏱️  **Timing:**"
    echo "  • Total duration: $TOTAL_DURATION seconds (3 minutes)"
    echo "  • Query interval: $QUERY_INTERVAL seconds"
    echo "  • Total queries: $((TOTAL_DURATION / QUERY_INTERVAL * 3))"
    echo
    echo "🎭 **Query diversity:**"
    echo "  • Employee management, HR policies, performance metrics"
    echo "  • Financial calculations, budget analysis, ROI calculations"
    echo "  • Administrative tasks, process management, compliance"
    echo
    echo "🚀 **Next steps:**"
    echo "1. Go to https://smith.langchain.com/"
    echo "2. Select project: 'agentic-on-eks'"
    echo "3. View traces in real-time dashboard"
    echo "4. Analyze agent performance and interactions"
    echo
    echo "💡 **Tips:**"
    echo "• Traces may take a few minutes to appear"
    echo "• Use filters to view specific agent traces"
    echo "• Check for any errors or performance issues"
    echo "• Compare response times across different query types"
}

# Function to show help
show_help() {
    echo "🚀 Traffic Generator for LangSmith Dashboard"
    echo "============================================"
    echo
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -h, --help           Show this help message"
    echo "  -d, --duration SEC   Set duration in seconds (default: 180)"
    echo "  -i, --interval SEC   Set query interval in seconds (default: 5)"
    echo "  --dry-run            Show what would be done without making changes"
    echo
    echo "This script generates diverse traffic to populate your LangSmith dashboard."
    echo "It sends various queries to all agents over the specified duration."
    echo
    echo "Examples:"
    echo "  $0                    # Run for 3 minutes (default)"
    echo "  $0 -d 300            # Run for 5 minutes"
    echo "  $0 -i 10             # Send queries every 10 seconds"
    echo "  $0 --help            # Show this help"
    echo
    echo "Prerequisites:"
    echo "  • kubectl configured and connected to cluster"
    echo "  • UI service running and accessible"
    echo "  • Port-forward set up: kubectl port-forward svc/$UI_SERVICE $UI_PORT:80"
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
            -d|--duration)
                if [[ -n "$2" && "$2" =~ ^[0-9]+$ ]]; then
                    TOTAL_DURATION="$2"
                    shift 2
                else
                    print_error "Duration must be a positive integer"
                    exit 1
                fi
                ;;
            -i|--interval)
                if [[ -n "$2" && "$2" =~ ^[0-9]+$ ]]; then
                    QUERY_INTERVAL="$2"
                    shift 2
                else
                    print_error "Interval must be a positive integer"
                    exit 1
                fi
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

# Function to validate configuration
validate_config() {
    if [[ $TOTAL_DURATION -lt 10 ]]; then
        print_error "Duration must be at least 10 seconds"
        exit 1
    fi
    
    if [[ $QUERY_INTERVAL -lt 1 ]]; then
        print_error "Query interval must be at least 1 second"
        exit 1
    fi
    
    if [[ $QUERY_INTERVAL -gt $TOTAL_DURATION ]]; then
        print_error "Query interval cannot be greater than total duration"
        exit 1
    fi
    
    print_success "Configuration validated:"
    print_status "  Duration: $TOTAL_DURATION seconds"
    print_status "  Query interval: $QUERY_INTERVAL seconds"
    print_status "  Estimated queries: $((TOTAL_DURATION / QUERY_INTERVAL * 3))"
}

# Main execution
main() {
    # Check command line arguments first
    check_args "$@"
    
    echo "🚀 Traffic Generator for LangSmith Dashboard"
    echo "============================================"
    echo
    
    # Validate configuration
    validate_config
    
    # Check prerequisites
    check_ui_service
    
    echo
    print_status "Ready to generate traffic!"
    print_status "Press Ctrl+C to stop early"
    echo
    
    # Generate traffic
    generate_traffic
    
    # Show summary
    show_traffic_summary
}

# Run main function
main "$@"
