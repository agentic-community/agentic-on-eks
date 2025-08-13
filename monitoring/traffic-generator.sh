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

# All queries go through Admin agent which routes to appropriate agent
# These queries are designed to test the routing logic and actual data/tools available

declare -a ALL_QUERIES=(
    # HR-related queries (will be routed to HR agent)
    "Show me details for employee EMP0001"
    "What is the information for employee EMP0005?"
    "Get employee directory information for EMP0010"
    "What's the leave policy for employee EMP0002?"
    "Show me the vacation policy for EMP0008"
    "How many vacation days does EMP0003 have left?"
    "Check remaining leave balance for employee EMP0012"
    "What's the PTO balance for EMP0020?"
    "How many public holidays are there in 2025 in the US?"
    "What are the leave policies available?"
    
    # Finance-related queries (will be routed to Finance agent)
    "Calculate annual salary for employee EMP0001"
    "What's the yearly salary for EMP0002?"
    "Show me the annual compensation for employee EMP0003"
    "Calculate EMP0004's annual earnings"
    "Calculate leave deduction for EMP0001 for 5 days off"
    "What's the salary deduction if EMP0002 takes 10 days leave?"
    "Calculate pay reduction for EMP0003 with 3 days absence"
    "Submit a raise of 5000 for employee EMP0001"
    "Process a salary increase of 3000 for EMP0004"
    "I want to give EMP0002 a raise of 4500"
    "What's the performance rating for EMP0001?"
    "Show me EMP0004's performance status"
    
    # General/Admin queries (handled directly by Admin agent)
    "I need help with employee onboarding"
    "What can you help me with?"
    "Tell me about the available services"
    "I need assistance with HR and Finance"
    "Help me understand what tools are available"
)

# Function to check if Admin Agent is accessible
check_admin_service() {
    print_status "Checking if Admin Agent service is accessible..."
    
    # Check if the Admin Agent service exists
    if kubectl get svc "agents-admin-agent-service" &> /dev/null; then
        print_success "Found Admin Agent service"
    else
        print_error "Admin Agent service not found"
        print_error "Please ensure the agents are deployed and running"
        exit 1
    fi
    
    # Check if port-forward to Admin Agent is working
    if curl -s -o /dev/null -w "%{http_code}" "http://localhost:8080/.well-known/agent.json" | grep -q "200"; then
        print_success "Admin Agent is accessible on port 8080"
        # Get agent info
        local agent_name=$(curl -s "http://localhost:8080/.well-known/agent.json" | grep -o '"name":"[^"]*"' | cut -d'"' -f4)
        if [[ -n "$agent_name" ]]; then
            print_success "Connected to: $agent_name"
        fi
    else
        print_error "Admin Agent not accessible on port 8080"
        print_error "Please run: kubectl port-forward svc/agents-admin-agent-service 8080:8080"
        print_error "This is required for the traffic generator to work"
        exit 1
    fi
}

# Function to send query to Admin Agent via HTTP
send_query() {
    local query="$1"
    local agent_type="$2"
    
    print_traffic "Sending: $query"
    
    # Generate UUIDs for the request
    local message_id=$(uuidgen 2>/dev/null || echo "$(date +%s)-$RANDOM")
    local task_id=$(uuidgen 2>/dev/null || echo "task-$(date +%s)-$RANDOM")
    local request_id=$(uuidgen 2>/dev/null || echo "req-$(date +%s)-$RANDOM")
    
    # Create JSON payload matching the UI's format
    local payload=$(cat <<EOF
{
  "id": "$request_id",
  "method": "message/send",
  "params": {
    "task": {
      "id": "$task_id",
      "name": "admin_query",
      "params": {},
      "status": {
        "state": "submitted",
        "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"
      }
    },
    "message": {
      "messageId": "$message_id",
      "id": "$message_id",
      "role": "user",
      "parts": [
        {
          "type": "text",
          "text": "$query"
        }
      ]
    }
  }
}
EOF
    )
    
    # Send request directly to Admin Agent service
    local admin_url="http://localhost:8080/"
    
    # First check if we can reach the Admin Agent
    if ! curl -s -o /dev/null -w "%{http_code}" "http://localhost:8080/.well-known/agent.json" | grep -q "200"; then
        print_warning "Admin Agent not accessible on port 8080"
        print_warning "Make sure to run: kubectl port-forward svc/agents-admin-agent-service 8080:8080"
        return 1
    fi
    
    # Send the actual query (write response to temp file to separate body from http_code)
    local temp_file=$(mktemp)
    local http_code=$(curl -s -X POST "$admin_url" \
        -H "Content-Type: application/json" \
        -d "$payload" \
        -w "%{http_code}" \
        -o "$temp_file" \
        2>/dev/null)
    
    local body=$(cat "$temp_file")
    rm -f "$temp_file"
    
    if [[ "$http_code" == "200" ]]; then
        print_success "Query processed successfully (HTTP $http_code)"
        # Optionally show a snippet of the response
        if [[ -n "$body" ]]; then
            local snippet=$(echo "$body" | grep -o '"text":"[^"]*"' | head -1 | cut -d'"' -f4 | cut -c1-50)
            if [[ -n "$snippet" ]]; then
                echo "  Response snippet: ${snippet}..."
            fi
        fi
    else
        print_error "Query failed (HTTP $http_code)"
        if [[ -n "$body" ]]; then
            echo "  Error: $(echo $body | cut -c1-100)..."
        fi
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
    print_status "All queries will be sent to Admin Agent for routing"
    echo
    
    while [[ $(date +%s) -lt $end_time ]]; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        local remaining=$((end_time - current_time))
        
        print_status "Elapsed: ${elapsed}s | Remaining: ${remaining}s | Queries sent: $query_count"
        
        # Send random query to Admin Agent (which will route appropriately)
        local query=$(get_random_query "${ALL_QUERIES[@]}")
        send_query "$query" "Admin Agent (will route to appropriate agent)"
        
        query_count=$((query_count + 1))
        
        echo
        
        # Wait for next query interval
        if [[ $(date +%s) -lt $end_time ]]; then
            print_status "Waiting ${QUERY_INTERVAL}s before next query..."
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
    echo "  • Total query types: ${#ALL_QUERIES[@]}"
    echo "  • HR-related queries: ~10 types (routed to HR agent)"
    echo "  • Finance-related queries: ~12 types (routed to Finance agent)"
    echo "  • General admin queries: ~5 types (handled by Admin agent)"
    echo
    echo "⏱️  **Timing:**"
    echo "  • Total duration: $TOTAL_DURATION seconds"
    echo "  • Query interval: $QUERY_INTERVAL seconds"
    echo "  • Total queries sent: $((TOTAL_DURATION / QUERY_INTERVAL))"
    echo
    echo "🎭 **Query routing flow:**"
    echo "  UI App → Admin Agent → Routes to HR/Finance based on query"
    echo
    echo "📝 **Query categories tested:**"
    echo "  • Employee directory lookups (EMP0001-EMP0030)"
    echo "  • Leave policies and vacation balances"
    echo "  • Annual salary calculations"
    echo "  • Leave deduction calculations"
    echo "  • Raise submissions and approvals"
    echo "  • Performance ratings"
    echo
    echo "🚀 **Next steps:**"
    echo "1. Go to https://smith.langchain.com/"
    echo "2. Select project: 'agentic-on-eks'"
    echo "3. View traces showing Admin Agent routing decisions"
    echo "4. Analyze HR and Finance agent responses"
    echo
    echo "💡 **What to look for in LangSmith:**"
    echo "• Admin Agent traces showing routing logic"
    echo "• HR Agent traces (CrewAI) for employee/leave queries"
    echo "• Finance Agent traces (LangGraph) for salary/raise queries"
    echo "• End-to-end latency for routed requests"
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
    echo "  • Admin Agent service running"
    echo "  • Port-forward set up: kubectl port-forward svc/agents-admin-agent-service 8080:8080"
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
    check_admin_service
    
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
