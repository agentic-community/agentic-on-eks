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
- **Database**: SQLite (auto-generated at runtime with 30 sample employees)
- **Features**:
  - 📋 Employee directory and information management
  - 🏖️ Vacation day calculations with leave policy management
  - 🎄 **MCP Server Integration**: Real-time public holiday data via Nager.Date API
  - 👥 CrewAI crew-based intelligent task execution
  - 📊 Dynamic leave balance tracking and policy assignments


#### 💰 Finance Agent (Financial Assistant)  
- **Framework**: LangGraph + A2A SDK
- **Database**: SQLite with pre-populated financial data
- **Features**:
  - 💵 Salary and compensation analysis
  - 📊 Leave deduction calculations with payroll impact
  - 🎯 Performance-based financial computations
  - 🏢 Department-wise financial reporting
  - 🧠 Optional Mem0 integration for conversation memory


### 🔧 Data & Integration Architecture

#### 🏗️ MCP Server Integration
The HR Agent leverages **Model Context Protocol (MCP)** for external data integration:
- **Public Holiday Service**: Real-time holiday data from Nager.Date API
- **Purpose**: Enhances vacation calculations with accurate holiday information
- **Integration**: Seamlessly integrated into CrewAI task workflows

#### 🗄️ Database Architecture
- **HR Database**: Auto-generated at startup with employee records, leave policies, and balance tracking
- **Finance Database**: Pre-populated with salary, performance, and department data
- **Data Synchronization**: Both databases share consistent employee IDs for cross-agent queries

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

# Build and push all container images
./build-images.sh
```

### 3️⃣ Deploy All Components

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

The platform supports intelligent query routing to specialized agents:

### 👥 HR Queries (→ HR Agent)

```bash
💬 "What is the name of employee EMP0002?"
# → Retrieves employee information from HR database

💬 "How many vacation days does employee EMP0001 have left?"  
# → Calculates remaining days based on policy, usage, and carryover

💬 "What public holidays are there in the US in 2025?"
# → Fetches real-time holiday data via MCP server integration

### 💰 Finance Queries (→ Finance Agent)

```bash
💬 "What is the annual salary of employee EMP0003?"
# → Retrieves salary and compensation details

💬 "Calculate leave deduction for EMP0002 for 5 days off"
# → Computes financial impact of time off on payroll

💬 "Show payroll information for EMP0001"
# → Combines salary, performance, and department data

💬 "What's the total salary expense for the Engineering department?"
# → Aggregates financial data by department
```

### 🎯 Admin Queries (→ Admin Agent)

```bash
💬 "Who is employee EMP0002 and what's their salary?"
# → Intelligently routes to both HR and Finance agents
# → Aggregates responses from multiple agents

💬 "I need help with vacation policy"  
# → Analyzes intent and routes to HR Agent
# → Handles ambiguous queries with LLM-powered routing
```

## 📚 Additional Documentation

- 🔐 [Authentication Setup](docs/auth.md)

## 📄 License

This project is licensed under the **Apache License 2.0** - see the [LICENSE](LICENSE) file for details.

---

**Made with ❤️ by Agentic Community**