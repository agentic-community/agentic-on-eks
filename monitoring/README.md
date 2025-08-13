# Monitoring Setup for Agentic-on-EKS

This directory contains the monitoring configuration for your AI agent platform deployed on Amazon EKS.

## 🚀 **Quick Setup (Recommended)**

```bash
# Step 1: Set up monitoring
./monitoring/deploy-monitoring.sh

# Step 2: Generate traffic to populate dashboard
./monitoring/traffic-generator.sh

# Step 3: View your dashboard at https://smith.langchain.com/
```

**That's it!** Two commands and you'll have a fully populated LangSmith dashboard.

## 🎯 **Overview**

The monitoring system provides:
- **LangSmith Cloud**: Full dashboard with charts and metrics
- **Agent tracing**: Monitor your AI agents' performance and interactions

## 🔄 **Complete Monitoring Workflow**

1. **Setup Monitoring** → `./monitoring/deploy-monitoring.sh`
   - Configures all agents with LangSmith environment variables
   - Restarts deployments to apply changes
   - Verifies setup is complete

2. **Generate Traffic** → `./monitoring/traffic-generator.sh`
   - Creates diverse queries across all agents
   - Runs for 3 minutes by default (configurable)
   - Generates rich trace data for analysis

3. **View Dashboard** → https://smith.langchain.com/
   - Real-time traces and performance metrics
   - Agent interaction analysis
   - Error tracking and debugging

## 🚀 **Quick Start - Get Full Dashboard with Charts**

### **LangSmith Cloud Setup (Recommended)**

This gives you the full dashboard with charts and comprehensive monitoring.

#### **Option 1: Automated Setup (Recommended)**
```bash
# Run the automated monitoring setup script
./monitoring/deploy-monitoring.sh
```

This script will:
- ✅ Check prerequisites (kubectl, deployments)
- ✅ Prompt for your LangSmith API key
- ✅ Automatically configure all agents
- ✅ Set all required environment variables
- ✅ Restart deployments to apply changes
- ✅ Verify the setup
- ✅ Test connectivity to LangSmith

#### **Option 2: Manual Setup**
If you prefer manual setup or need to customize:

**Step 1: Get Your LangSmith Cloud API Key**
1. Go to [https://smith.langchain.com/](https://smith.langchain.com/)
2. Sign up/Sign in to your account
3. Navigate to your project settings
4. Copy your API key (starts with `ls_...`)

**Step 2: Switch Agents to LangSmith Cloud**
```bash
# Update API key for all agents
kubectl set env deployment/agents-admin-agent LANGCHAIN_API_KEY=ls_your_actual_api_key_here
kubectl set env deployment/agents-finance-agent LANGCHAIN_API_KEY=ls_your_actual_api_key_here  
kubectl set env deployment/agents-hr-agent LANGCHAIN_API_KEY=ls_your_actual_api_key_here

# Update endpoint to LangSmith Cloud
kubectl set env deployment/agents-admin-agent LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
kubectl set env deployment/agents-finance-agent LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
kubectl set env deployment/agents-hr-agent LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
```

#### **Step 3: Access Your Dashboard**
1. Go to [https://smith.langchain.com/](https://smith.langchain.com/)
2. Select your project (should be "agentic-on-eks")
3. Enjoy your full dashboard with:
   - 📊 Real-time charts and metrics
   - 🔍 Trace visualization
   - 📈 Performance analytics
   - 🚀 Agent interaction logs

## 🏗️ **Architecture**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Your Agents   │───▶│  LangSmith Cloud │───▶│  Full Dashboard │
│ (Admin/HR/Fin)  │    │   (API Endpoint) │    │   with Charts   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 📁 **Files in This Directory**

- `deploy-monitoring.sh` - **Automated monitoring setup script (recommended)**
- `traffic-generator.sh` - **Traffic generator to populate LangSmith dashboard**
- `README.md` - This documentation

## 🔧 **Configuration Details**

### **Environment Variables for Cloud LangSmith**
```yaml
LANGCHAIN_TRACING_V2: "true"           # Enable tracing
LANGCHAIN_ENDPOINT: "https://api.smith.langchain.com"  # Cloud endpoint
LANGCHAIN_API_KEY: "ls_your_api_key"   # Your API key
LANGCHAIN_PROJECT: "agentic-on-eks"    # Project name
LANGCHAIN_TRACING: "true"              # Enable tracing
```

## 🚀 **Getting Started**

### **Complete End-to-End Setup (Recommended)**
```bash
# 1. Set up monitoring (configures all agents)
./monitoring/deploy-monitoring.sh

# 2. Generate traffic to populate dashboard
./monitoring/traffic-generator.sh

# 3. View your populated dashboard
# Go to: https://smith.langchain.com/
# Select project: 'agentic-on-eks'
```

### **For Manual Setup**
1. Get your LangSmith Cloud API key
2. Update agent environment variables (see Step 2 above)
3. Access your dashboard at [https://smith.langchain.com/](https://smith.langchain.com/)

## 📊 **What You'll See in LangSmith Cloud**

- **Real-time Traces**: Every agent interaction and LLM call
- **Performance Metrics**: Response times, token usage, cost tracking
- **Agent Interactions**: How agents communicate and route requests
- **Error Tracking**: Failed requests and debugging information
- **Custom Metadata**: User IDs, session tracking, business metrics

## 🔍 **Troubleshooting**

### **Common Issues**
1. **No traces appearing**: Check API key and endpoint configuration
2. **Authentication errors**: Verify your LangSmith Cloud API key
3. **Project not found**: Ensure project name matches in LangSmith Cloud

### **Verification Commands**
```bash
# Check agent environment variables
kubectl get deployment agents-admin-agent -o yaml | grep -A 10 env:

# Test LangSmith connectivity
kubectl exec -it deployment/agents-admin-agent -- curl -H "Authorization: Bearer $LANGCHAIN_API_KEY" https://api.smith.langchain.com/traces
```

### **Using the Automated Script for Troubleshooting**
```bash
# Get help and see what the script does
./monitoring/deploy-monitoring.sh --help

# Re-run the setup if you need to reconfigure
./monitoring/deploy-monitoring.sh

# Check if deployments exist (script will do this automatically)
kubectl get deployments | grep agents-

# Check specific agent deployment status
kubectl get deployment agents-admin-agent
kubectl get deployment agents-finance-agent
kubectl get deployment agents-hr-agent
```

## 🎯 **Next Steps**

1. **Get your LangSmith Cloud API key** from [https://smith.langchain.com/](https://smith.langchain.com/)
2. **Update agent environment variables** using the kubectl commands above
3. **Monitor your agents** in real-time through the cloud dashboard
4. **Set up alerts** for performance issues or errors

## 💡 **Benefits of Cloud LangSmith**

- **No local infrastructure** to manage or maintain
- **Full dashboard experience** with charts and analytics
- **Automatic scaling** and high availability
- **Professional monitoring** with enterprise features
- **Cost-effective** usage-based pricing
- **Team collaboration** with shared dashboards

## 🚀 **Benefits of Automated Setup Script**

- **One-command setup** - no manual kubectl commands needed
- **Error prevention** - validates API key format and prerequisites
- **Comprehensive verification** - ensures all agents are properly configured
- **Automatic restarts** - deployments restart to pick up new environment variables
- **Connectivity testing** - verifies LangSmith API access
- **Clear next steps** - provides guidance on what to do after setup
- **Troubleshooting help** - includes common commands for debugging

## 🎯 **Populate Your LangSmith Dashboard**

After setting up monitoring, you'll want to generate some traffic to see traces in your dashboard.

### **Quick Traffic Generation**
```bash
# Generate 3 minutes of diverse traffic to all agents
./monitoring/traffic-generator.sh
```

### **Custom Traffic Generation**
```bash
# Generate traffic for 5 minutes
./monitoring/traffic-generator.sh -d 300

# Send queries every 10 seconds instead of 5
./monitoring/traffic-generator.sh -i 10

# Get help and see all options
./monitoring/traffic-generator.sh --help
```

### **What the Traffic Generator Does**
- 🎭 **Diverse queries** - 30+ different query types across all agents
- ⏱️ **Realistic timing** - configurable intervals and duration
- 🔄 **Agent coverage** - hits Admin, HR, and Finance agents
- 📊 **Rich traces** - creates comprehensive monitoring data
- 🎯 **Dashboard ready** - populates LangSmith with real activity
