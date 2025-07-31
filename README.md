# 🤖 Agentic AI on EKS

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?logo=kubernetes&logoColor=white)](https://kubernetes.io/)
[![AWS](https://img.shields.io/badge/AWS-FF9900?logo=amazon-aws&logoColor=white)](https://aws.amazon.com/)
[![Helm](https://img.shields.io/badge/Helm-0F1689?logo=helm&logoColor=white)](https://helm.sh/)

This project demonstrates a **multi-agent platform** deployed on Amazon EKS that simulates an organizational assistant. It features an **Admin/Supervisor agent** that intelligently routes queries to specialized **HR** and **Finance** agents, showcasing agent-to-agent collaboration using the **Agent-to-Agent (A2A) protocol** with OAuth 2.0 security.

## 🏗️ Architecture Overview

The platform implements a **microservices architecture** where specialized agents collaborate to handle different business domains with intelligent routing and comprehensive security.

### 🔧 Components

#### 🖥️ UI Application
- **Framework**: Streamlit web application
- **Authentication**: Okta OAuth 2.0 authorization code flow
- **Features**: Interactive chat interface with agent communication
- **Deployment**: Containerized on Kubernetes

#### 🎯 Admin Agent (Supervisor & Router)
- **Framework**: A2A SDK + LangChain
- **AI Model**: AWS Bedrock Claude 3 Sonnet
- **Features**:
  - 🧠 LLM-powered intelligent query routing
  - 🔄 Fallback keyword-based routing for reliability
  - 🔗 A2A client for downstream agent communication
  - 🔐 OAuth client credentials flow for secure inter-agent communication


#### 👥 HR Agent (Employee Assistant)
- **Framework**: CrewAI + A2A SDK
- **Database**: SQLite for employee data (30 sample employees)
- **Features**:
  - 📋 Employee directory and information management
  - 🏖️ Vacation day calculations and leave policies
  - 🎄 **MCP Server Integration**: Public holiday data via Nager.Date API
  - 👥 CrewAI crew-based task execution
- **Tools & Database Schema**:
  - `employee_directory_service()`: Fetches employee details by ID
  - `vacation_days_service()`: Calculates remaining vacation days
  - `get_public_holidays()`: MCP tool for holiday information
  - SQLite schema: `employees` table with `employee_id`, `name`, `start_date`, `vacation_days_used`, `total_vacation_days`


#### 💰 Finance Agent (Financial Assistant)  
- **Framework**: LangGraph + A2A SDK
- **Database**: SQLite for financial data (synchronized with HR data)
- **Features**:
  - 💵 Salary calculations and financial analysis
  - 📊 Leave deduction calculations and payroll processing
  - 🧠 Optional Mem0 integration for memory management
- **Tools & Database Schema**:
  - `get_employee_performance()`: Retrieves performance metrics
  - `get_employee_financial_data()`: Fetches salary and financial info
  - `calculate_leave_deduction()`: Computes payroll deductions
  - SQLite schema: `employees` table with `employee_id`, `name`, `hourly_rate`, `annual_salary`, `performance`, `department`


### 🔧 Tools & Data Architecture

#### 🏗️ MCP Server Integration
The HR Agent implements **Model Context Protocol (MCP)** servers for external data integration:

**📅 Public Holiday MCP Server** (`nager_mcp_server.py`)
- **Purpose**: Fetches real-time public holiday data for vacation calculations
- **API**: Nager.Date REST API (`https://date.nager.at/api/v3/`)
- **Tool**: `get_public_holidays(year, country_code)`
- **Returns**: Holiday summary with dates and names for specified year/country
- **Usage**: Integrated into CrewAI vacation calculations for accurate leave planning

#### 🗄️ SQLite Database Tools

**👥 HR Agent Database** (`hr_database.sqlite`)
```sql
-- Employee master data
CREATE TABLE employees (
    employee_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    start_date TEXT NOT NULL,
    vacation_days_used INTEGER DEFAULT 0,
    total_vacation_days INTEGER DEFAULT 20
);

-- 30 sample employees auto-generated on startup
-- Path: /app/data/hr_database.sqlite (containerized)
```

**💰 Finance Agent Database** (`employee.db`)
```sql
-- Financial and performance data  
CREATE TABLE employees (
    employee_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    hourly_rate REAL NOT NULL,
    annual_salary REAL NOT NULL,
    performance TEXT DEFAULT 'Good',
    department TEXT NOT NULL
);

-- Synchronized employee IDs with HR database
-- Contains salary, performance, and payroll data
```

#### 🛠️ Agent Tools Overview

| Agent | Tool Name | Function | Data Source |
|-------|-----------|----------|-------------|
| **HR** | `employee_directory_service()` | Employee lookup | SQLite HR DB |
| **HR** | `vacation_days_service()` | Vacation calculations | SQLite HR DB |  
| **HR** | `get_public_holidays()` | Holiday information | MCP Server → Nager API |
| **Finance** | `get_employee_performance()` | Performance metrics | SQLite Finance DB |
| **Finance** | `get_employee_financial_data()` | Salary & financial info | SQLite Finance DB |
| **Finance** | `calculate_leave_deduction()` | Payroll calculations | SQLite Finance DB |

### 🔒 Security Architecture

- **🔐 OAuth 2.0 Flow**: Complete authentication using Okta
- **🏷️ JWT Token Validation**: RS256 signature verification with JWKS
- **🎯 Scope-based Authorization**: Fine-grained access control
- **🤝 Agent-to-Agent Security**: Client credentials flow for inter-agent communication

## ✨ Key Features

- ✅ **A2A Implementation** with OAuth 2.0 security
- ✅ **Intelligent Query Routing** using AWS Bedrock LLM
- ✅ **Kubernetes-native Deployment** with Helm charts
- ✅ **Dual Deployment Modes**: Demo (no auth) and Secure (OAuth)


## 📋 Prerequisites

Before deploying the platform, ensure you have:

### Required Tools
- 🔧 **AWS CLI** configured with appropriate permissions
- 🐳 **Docker** installed and running  
- ⚓ **kubectl** configured for your EKS cluster
- 🎯 **Helm 3.8+** for Kubernetes deployments

### AWS Services
- 🤖 **AWS Bedrock** access for Claude 3 Sonnet model
- 📦 **Amazon ECR** for container registry
- ☁️ **Amazon EKS** cluster deployed

### Optional Services
- 🔐 **Okta Account** for OAuth 2.0 (secure mode only)
- 🧠 **Mem0 API Key** for external memory features

## 🚀 Quick Start

### 1️⃣ Infrastructure Setup

Deploy your EKS cluster using Terraform:

```bash
cd infra

# Configure your AWS settings
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# Deploy infrastructure
terraform init
terraform apply
```

### 2️⃣ Build Container Images

Build and push all agent container images to ECR:

```bash
# Set your AWS account ID
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Build and push all images
./build-images.sh
```

### 3️⃣ Deploy the Platform

Choose your deployment mode based on your requirements:

## 🎭 Demo Mode Deployment

Suitable for **development**, and **testing** purposes, without OAuth complexity.

### Features
- 🚫 **No Authentication**: Bypasses OAuth for easy testing
- ⚡ **Quick Setup**: No OKTA configuration required  
- 🧪 **Demo User**: Pre-configured test user
- 🔓 **Open Access**: All agents accessible without tokens

### Deploy in Demo Mode

```bash
# Set required environment variable
export ACCOUNT_ID=your-aws-account-id

# Deploy in demo mode
./deploy-helm.sh -m demo
```

### Test Demo Deployment

```bash
# Port-forward the UI application
kubectl port-forward svc/agents-ui-app-service 8501:80

# Open browser to http://localhost:8501
# No login required - start chatting immediately!
```

## 🔒 Secure Mode Deployment  

Recommended for **production** environments with full OAuth 2.0 authentication.

### Features
- 🔐 **Full OAuth 2.0**: Complete Okta integration
- 🛡️ **Token Validation**: JWT verification on all requests
- 👤 **User Authentication**: Okta login required
- 🔑 **Agent-to-Agent Security**: Client credentials flow

### Prerequisites for Secure Mode

1. **Okta Developer Account** with:
   - Authorization Server configured
   - Two OAuth applications created:
     - `All-Agents-App`
     - `Agent-UI-App`

2. **Required Environment Variables**:

```bash
# AWS Configuration
export ACCOUNT_ID=your-aws-account-id

# Okta Configuration  
export OKTA_DOMAIN=your-domain.okta.com
export OKTA_AUTH_SERVER_ID=your-auth-server-id

# Admin Agent OAuth (All-Agents-App)
export OKTA_ADMIN_CLIENT_ID=your-admin-client-id
export OKTA_ADMIN_CLIENT_SECRET=your-admin-secret

# UI OAuth (Agent-UI-App)  
export OKTA_UI_CLIENT_ID=your-ui-client-id
export OKTA_UI_CLIENT_SECRET=your-ui-secret
export OKTA_REDIRECT_URI=http://localhost:8501  # Optional
```

### Deploy in Secure Mode

```bash
# Deploy with OAuth enabled
./deploy-helm.sh -m secure
```

### Test Secure Deployment

```bash
# Port-forward the UI application
kubectl port-forward svc/agents-ui-app-service 8501:80

# Open browser to http://localhost:8501
# You'll be redirected to Okta for authentication
```

## 🔄 Management Commands

### Upgrade Existing Deployment

```bash
# Upgrade demo deployment
./deploy-helm.sh -m demo -a upgrade

# Upgrade secure deployment  
./deploy-helm.sh -m secure -a upgrade
```



## 🧪 Testing Agent Communication

The platform supports intelligent query routing to appropriate agents:

### 👥 HR Queries (→ HR Agent)
The HR Agent uses **CrewAI crews**

```bash
💬 "What is the name of employee EMP0002?"

💬 "How many vacation days does employee EMP0001 have left?"  
# → Uses: vacation_days_service() → SQLite HR DB + MCP holiday server

💬 "When is the next public holiday in 2025?"
# → Uses: get_public_holidays(2025, "US") → MCP Server → Nager.Date API

### 💰 Finance Queries (→ Finance Agent)
The Finance Agent uses **LangGraph workflows** 

```bash
💬 "What is the annual salary of employee EMP0003?"
# → Uses: get_employee_financial_data() → SQLite Finance DB  

💬 "Calculate leave deduction for EMP0002 for 5 days off"
# → Uses: calculate_leave_deduction() → Multi-tool workflow

💬 "Show payroll information for EMP0001"
# → Uses: get_employee_financial_data() + get_employee_performance()

💬 "Update hourly rate for EMP0001 to $75"  
# → Uses: calculate_leave_deduction() with update flag
# → SQL UPDATE on employees table in SQLite database
```

### 🎯 Admin Queries (→ Admin Agent)
The Admin Agent uses **LLM-powered routing** with **fallback logic**:

```bash
💬 "Route this to HR: employee information"
# → Identifies HR-related keywords
# → Routes to HR Agent via A2A protocol

💬 "Send to finance: salary details"  
# → Identifies finance-related keywords
# → Routes to Finance Agent with OAuth token
```

## 🐛 Troubleshooting

### Common Issues

#### 📦 Pod Issues
```bash
# Check pod status
kubectl get pods

# View pod logs
kubectl logs <pod-name>

# Describe pod for events
kubectl describe pod <pod-name>
```

#### 🔐 Authentication Issues
- **Demo Mode**: Ensure `DEMO_MODE=true` is set
- **Secure Mode**: Verify all OKTA environment variables
- **Token Issues**: Check Okta application configuration

#### 🌐 Networking Issues
```bash
# Test service connectivity
kubectl get svc

# Check ingress/port-forwarding
kubectl port-forward svc/agents-ui-app-service 8501:80
```

#### 🚀 Image Pull Issues
- Verify AWS account ID is correct
- Ensure ECR repositories exist
- Check IAM permissions for ECR access

## 📚 Additional Documentation

- 🔐 [Authentication Setup](docs/auth.md) 


## 🛡️ Security Best Practices

### Production Deployment Recommendations

- 🔐 **AWS Secrets Manager**: Store sensitive credentials
- 🌐 **Ingress & TLS**: Use proper domain with HTTPS
- 🎯 **Fine-grained Scopes**: Implement specific agent permissions
- ✅ **Input Validation**: Sanitize all user inputs
- 🛡️ **Bedrock Guardrails**: Enable AWS Bedrock security features
- 📊 **Monitoring**: Implement logging and observability
- 🔄 **Backup Strategy**: Regular data backups

## 📄 License

This project is licensed under the **Apache License 2.0** - see the [LICENSE](LICENSE) file for details.

---

**Made with ❤️ for the Kubernetes and AI community**