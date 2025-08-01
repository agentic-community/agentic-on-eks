# 🤖 Agentic AI on EKS

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?logo=kubernetes&logoColor=white)](https://kubernetes.io/)
[![AWS](https://img.shields.io/badge/AWS-FF9900?logo=amazon-aws&logoColor=white)](https://aws.amazon.com/)
[![Helm](https://img.shields.io/badge/Helm-0F1689?logo=helm&logoColor=white)](https://helm.sh/)

This project demonstrates a **multi-agent platform** deployed entirely on Amazon EKS that simulates an organizational assistant. It features an **Admin/Supervisor agent** that intelligently routes queries to specialized **HR** and **Finance** agents, showcasing agent-to-agent collaboration using the **Agent-to-Agent (A2A) protocol** with OAuth 2.0 security.

## 🏗️ Architecture

The platform simulates an organizational assistant for employee services, implementing a multi-agent workflow where specialized agents collaborate to handle HR inquiries, financial queries, and administrative tasks with skill-based routing and built-in security.

### 🤝 Agent-to-Agent (A2A) Protocol Implementation

The platform showcases **Agent-to-Agent (A2A) communication pattern** where:
- **HR and Finance Agents** act as **A2A servers**, exposing their specialized capabilities through standardized endpoints
- **Admin Agent** serves as an **A2A client**, discovering agent capabilities and routing user requests
- **OAuth Security**: All inter-agent communication is secured using OAuth 2.0 client credentials flow (via Okta in secure mode), ensuring authenticated and authorized access

### 📊 Functional Overview

```mermaid
graph TB
    subgraph "<b>EKS Cluster</b>"
        subgraph "Frontend"
            UI["🖥️ Chatbot<br/>"]
        end
        
        subgraph "Agent Layer"
            Admin["🎯 Admin Agent<br/>(A2A Client)<br/>"]
            HR["👥 HR Agent<br/>(A2A Server)<br/>"]
            Finance["💰 Finance Agent<br/>(A2A Server)<br/>"]
        end
        
        subgraph "Data Layer"
            HRDB[("📊 HR Database")]
            FinDB[("💵 Finance Database")]
        end
        
        subgraph "Integration"
            MCP["🎄 MCP Server<br/>Holiday API"]
        end
    end
    
    subgraph "External Services"
        Okta["🔐 Okta<br/>OAuth Provider"]
        Bedrock["🤖 AWS Bedrock<br/>LLM Provider"]
        Nager["📅 Nager.Date<br/>Holiday API"]
    end
    
    User["👤 User"] -->|"Login"| UI
    UI <-->|"OAuth Flow"| Okta
    UI -->|"Query"| Admin
    Admin -->|"Route Query"| HR
    Admin -->|"Route Query"| Finance
    HR <-->|"Employee Data"| HRDB
    Finance <-->|"Finance Data"| FinDB
    HR <-->|"Holiday Data"| MCP
    MCP <-->|"API Call"| Nager
    Admin <-->|"LLM Routing"| Bedrock
    HR <-->|"CrewAI Tasks"| Bedrock
    Finance <-->|"LangGraph Flow"| Bedrock
    
    style UI fill:#4A5568,stroke:#E2E8F0,stroke-width:2px,color:#F7FAFC
    style Admin fill:#2D3748,stroke:#E2E8F0,stroke-width:2px,color:#F7FAFC
    style HR fill:#2B6CB0,stroke:#E2E8F0,stroke-width:2px,color:#F7FAFC
    style Finance fill:#2F855A,stroke:#E2E8F0,stroke-width:2px,color:#F7FAFC
    style Okta fill:#553C9A,stroke:#E2E8F0,stroke-width:2px,color:#F7FAFC
    style Bedrock fill:#C05621,stroke:#E2E8F0,stroke-width:2px,color:#F7FAFC
    style HRDB fill:#1A365D,stroke:#E2E8F0,stroke-width:2px,color:#F7FAFC
    style FinDB fill:#22543D,stroke:#E2E8F0,stroke-width:2px,color:#F7FAFC
    style MCP fill:#742A2A,stroke:#E2E8F0,stroke-width:2px,color:#F7FAFC
    style Nager fill:#744210,stroke:#E2E8F0,stroke-width:2px,color:#F7FAFC
    style User fill:#1A202C,stroke:#E2E8F0,stroke-width:2px,color:#F7FAFC
    
    classDef transparentSubgraph fill:transparent,stroke:#718096,stroke-width:2px,stroke-dasharray:5 5
    class Frontend,AgentLayer,DataLayer,Integration,External transparentSubgraph
```

### 🔧 Components

#### 🖥️ UI Application
- **Framework**: Streamlit web application
- **Authentication**: Okta OAuth 2.0 authorization code flow
- **Features**: Interactive chat interface with agent communication

#### 🎯 Admin Agent (Supervisor & Router)
- **Framework**: A2A SDK + LangChain
- **AI Model**: Uses Amazon Bedrock as Model Provider
- **Features**:
  - 🧠 LLM-powered intelligent query routing
  - 🔄 Fallback keyword-based routing for reliability
  - 🔗 A2A client for downstream agent communication
  - 🔐 OAuth client credentials flow for secure inter-agent communication


#### 👥 HR Agent (Employee Assistant)
- **Framework**: CrewAI + A2A SDK
- **Database**: SQLite
- **Features**:
  - 📋 Employee directory and information management
  - 🏖️ Vacation day calculations with leave policy management
  - 🎄 **MCP Server Integration**: Real-time public holiday data via Nager.Date API
  - 👥 CrewAI crew-based task execution


#### 💰 Finance Agent (Financial Assistant)  
- **Framework**: LangGraph + A2A SDK
- **Database**: SQLite with pre-populated financial data
- **Features**:
  - 💵 Salary and compensation analysis
  - 📊 Leave deduction calculations with payroll impact
  - 🎯 Performance-based financial computations



### 🔧 Tools Integration with MCP

#### 🏗️ MCP Integration
The HR Agent leverages **Model Context Protocol (MCP)** for external data integration:
- **Public Holiday Service**: Real-time holiday data from Nager.Date API
- **Purpose**: Enhances vacation calculations with accurate holiday information
- **Integration**: Seamlessly integrated into CrewAI task workflows

#### 🗄️ Database (SQLite)
- **HR Database**: Auto-generated at startup with employee records, leave policies, and balance tracking
- **Finance Database**: Pre-populated with salary, performance, and department data

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
cd ..
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

### 👥 HR Sample Queries (→ HR Agent)

```bash
💬 "What is the name of employee EMP0002?"
# → Retrieves employee information from HR database

💬 "How many vacation days does employee EMP0001 have left?"  
# → Calculates remaining days based on policy, usage, and carryover
```

### 💰 Finance Queries (→ Finance Agent)

```bash
💬 "What is the annual salary of employee EMP0003?"
# → Retrieves salary and compensation details
```

## 📚 Additional Documentation

- 🔐 [Authentication Setup](docs/auth.md)

## 📄 License

This project is licensed under the **Apache License 2.0** - see the [LICENSE](LICENSE) file for details.

---