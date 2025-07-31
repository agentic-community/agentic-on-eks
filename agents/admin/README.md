# Admin Agent

The Admin Agent is an intelligent routing agent that serves as a supervisor for HR and Finance agents in the system. It demonstrates true agent-to-agent communication using the A2A protocol.

## Architecture

The Admin Agent acts as both:
- **A2A Server**: Receives queries from the UI application
- **A2A Client**: Forwards queries to HR and Finance agents based on intelligent routing

## Features

- **Intelligent Routing**: Uses AWS Bedrock LLM to analyze queries and determine the appropriate target agent
- **A2A Protocol Compliance**: Uses the latest A2A SDK for all communications
- **Agent Discovery**: Automatically discovers HR and Finance agents via their `.well-known/agent.json` endpoints
- **Error Handling**: Robust error handling and fallback mechanisms
- **No OAuth Dependency**: Configured for public authentication to simplify testing

## Query Routing Logic

The Admin Agent analyzes incoming queries and routes them based on content:

- **HR Agent**: Employee information, vacation days, leave policies, public holidays
- **Finance Agent**: Salary calculations, pay deductions, raises, financial data

## Communication Flow

```
UI Application → Admin Agent → HR/Finance Agent → Admin Agent → UI Application
```

## Running the Agent

```bash
# Install dependencies
uv sync

# Run locally
python __main__.py --host 0.0.0.0 --port 8080

# Run in Kubernetes
kubectl apply -f k8s/admin-agent-deploy.yaml
```

## Environment Variables

- `HR_HOST`: Hostname for HR agent (default: hr-agent-service.default.svc.cluster.local)
- `HR_PORT`: Port for HR agent (default: 80)
- `FINANCE_HOST`: Hostname for Finance agent (default: finance-agent-service.default.svc.cluster.local)
- `FINANCE_PORT`: Port for Finance agent (default: 80)
- `BEDROCK_MODEL_ID`: AWS Bedrock model for routing decisions
- `AWS_REGION`: AWS region for Bedrock

## Testing

Send queries to the Admin Agent and observe how they are routed:

```bash
# HR query example
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{"method": "send_task", "params": {"message": {"parts": [{"text": "How many vacation days does EMP0002 have?"}]}}}'

# Finance query example  
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{"method": "send_task", "params": {"message": {"parts": [{"text": "What is the salary of EMP0001?"}]}}}'
```