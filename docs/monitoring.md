# 📊 Monitoring & Observability with LangFuse

## Overview

This project includes a fully integrated, **self-hosted LangFuse deployment** on Amazon EKS for comprehensive agent observability. LangFuse provides distributed tracing, performance metrics, and cost tracking for all LLM-powered agents in the system.

## Architecture

### LangFuse Components

The self-hosted LangFuse deployment includes:

| Component | Purpose | Status |
|-----------|---------|--------|
| **LangFuse Web** | Main application server and UI | ✅ Enabled |
| **LangFuse Worker** | Background job processor | ✅ Enabled |
| **PostgreSQL** | Primary data storage for traces, metrics, and configuration | ✅ Enabled |
| **ClickHouse Cluster** | Time-series analytics for high-volume trace data (3-node sharded cluster) | ✅ Enabled |
| **Redis** | Caching layer and queue management | ✅ Enabled |
| **S3 (MinIO)** | Object storage for media and large payloads | ✅ Enabled |
| **ZooKeeper** | Distributed coordination for ClickHouse cluster | ✅ Enabled |

> **Note**: The full production-ready stack is deployed by default, providing scalability and high performance for trace analytics.

### Deployment Method

LangFuse is deployed using:
- **Helm Chart**: Official LangFuse Helm chart from `https://langfuse.github.io/langfuse-helm`
- **Terraform Module**: Custom `langfuse.tf` module that manages the Helm release
- **Kubernetes Namespace**: Deployed in a dedicated `langfuse` namespace

## Setup & Configuration

### 1. Enable LangFuse in Terraform

Update your `terraform.tfvars`:

```hcl
# Core LangFuse enablement
enable_langfuse = true

# Enable persistent storage (recommended for production)
enable_langfuse_persistence = true

# Optional: Configure LangFuse API keys after initial setup
# langfuse_public_key = "pk-lf-xxxxxxxx"
# langfuse_secret_key = "sk-lf-xxxxxxxx"
```

### 2. Deploy Infrastructure

```bash
cd infra

# Initialize and apply Terraform
terraform init
terraform apply
```

This will deploy:
- LangFuse web and worker pods
- PostgreSQL with persistent storage
- ClickHouse 3-node sharded cluster
- Redis for caching
- MinIO for S3-compatible storage
- ZooKeeper for cluster coordination
- Kubernetes secrets for agent integration

### 3. Verify Deployment

Check all components are running:

```bash
kubectl get pods -n langfuse

# Expected output:
NAME                               READY   STATUS    RESTARTS   AGE
langfuse-clickhouse-shard0-0       1/1     Running   0          4h
langfuse-clickhouse-shard0-1       1/1     Running   0          4h
langfuse-clickhouse-shard0-2       1/1     Running   0          4h
langfuse-postgresql-0              1/1     Running   0          4h
langfuse-redis-primary-0           1/1     Running   0          4h
langfuse-s3-xxxxxxxxx-xxxxx        1/1     Running   0          4h
langfuse-web-xxxxxxxxx-xxxxx       1/1     Running   0          4h
langfuse-worker-xxxxxxxxx-xxxxx    1/1     Running   0          4h
langfuse-zookeeper-0               1/1     Running   0          4h
```

### 4. Initial LangFuse Setup

```bash
# Port-forward to access LangFuse UI
kubectl port-forward -n langfuse svc/langfuse 3000:3000

# Open browser to http://localhost:3000
```

First-time setup:
1. Create your admin account
2. Navigate to **Settings → API Keys**
3. Create a new API key pair
4. Save the public and secret keys

### 5. Configure Agent Integration

Update `terraform.tfvars` with your API keys:

```hcl
langfuse_public_key = "pk-lf-xxxxxxxx"
langfuse_secret_key = "sk-lf-xxxxxxxx"
```

Apply the configuration:

```bash
terraform apply
```

This creates a `langfuse-credentials` secret that agents automatically use.

### 6. Rebuild and Deploy Agents

```bash
# Rebuild agent images with LangFuse integration
./build-images.sh admin hr finance

# Deploy agents - they'll automatically detect LangFuse
./deploy-helm.sh -m demo
```

## Agent Integration Details

### How Agents Connect to LangFuse

Each agent includes the `langfuse_config.py` utility that:
1. Reads credentials from environment variables (injected via Kubernetes secrets)
2. Connects to LangFuse at `http://langfuse.langfuse.svc.cluster.local:3000`
3. Automatically instruments all LLM calls and agent interactions

### Instrumented Agents

| Agent | Framework | LangFuse Integration |
|-------|-----------|---------------------|
| **Admin Agent** | Strands | ✅ Full trace instrumentation |
| **HR Agent** | CrewAI | ✅ Task and tool tracking |
| **Finance Agent** | LangGraph | ✅ Graph execution tracing |

## Testing & Validation

### 1. Verify LangFuse Deployment

```bash
# Check all pods are running
kubectl get pods -n langfuse

# Check services
kubectl get svc -n langfuse
```

### 2. Test Agent Communication

Send test queries through the UI:

```bash
# Port-forward the UI
kubectl port-forward svc/agents-ui-app-service 8501:80

# Open http://localhost:8501 and send queries like:
# - "What is the name of employee EMP0002?"
# - "How many vacation days does EMP0001 have?"
# - "What is the salary of EMP0003?"
```

### 3. View Traces in LangFuse

Access the LangFuse dashboard:

```bash
kubectl port-forward -n langfuse svc/langfuse 3000:3000
# Open http://localhost:3000
```

Navigate to view traces:

1. **Traces Tab**: See all agent interactions
   - Click on any trace to see the full conversation flow
   - View the Admin → HR/Finance agent routing
   - See LLM calls with token counts

2. **Dashboard Tab**: View aggregated metrics
   - Request volume over time
   - Latency percentiles (P50, P90, P99)
   - Error rates and success rates
   - Token usage and costs

3. **Sessions Tab**: Track complete user conversations
   - See how queries flow through multiple agents
   - Understand the full context of multi-turn conversations

### 4. Filtering and Analysis

To analyze specific agents:

1. **Filter by Agent Name**:
   - In Traces view, use the filter dropdown
   - Select `metadata.agent_name` or `name` field
   - Choose specific agent (admin, hr, finance)

2. **Filter by Time Range**:
   - Use the time selector in top-right
   - View last hour, day, week, or custom range

3. **Filter by Status**:
   - Success vs. Error traces
   - High latency traces (>2s)

4. **Search Capabilities**:
   - Search by user input text
   - Search by agent response content
   - Search by error messages

## Metrics & Observability

### Key Metrics Available

| Metric | Description | Where to Find |
|--------|-------------|---------------|
| **Latency** | Response time distribution | Dashboard → Latency chart |
| **Throughput** | Requests per minute/hour | Dashboard → Request volume |
| **Token Usage** | Input/output tokens per request | Traces → Individual trace details |
| **Cost** | Estimated LLM costs | Dashboard → Cost tracking |
| **Error Rate** | Failed requests percentage | Dashboard → Success rate |
| **Agent Utilization** | Which agents handle most queries | Dashboard → Group by metadata.agent_name |

### Performance Optimization

Monitor these indicators:
- **P99 Latency > 5s**: Consider optimizing agent logic
- **High Error Rate**: Check agent logs for issues
- **Token Spike**: Review prompts for efficiency
- **Uneven Distribution**: Admin agent routing may need tuning

## Component Details

### ClickHouse Cluster
- **3-node sharded cluster** for horizontal scaling
- Handles high-volume trace ingestion
- Provides fast analytics queries
- Managed by ZooKeeper for coordination

### Redis
- Caches frequently accessed data
- Manages background job queues
- Improves dashboard performance

### MinIO (S3)
- Stores large trace payloads
- Archives historical data
- Provides S3-compatible API

## Troubleshooting

### LangFuse Not Receiving Traces

1. Check secret is created:
```bash
kubectl get secret langfuse-credentials -n default
kubectl get secret langfuse-credentials -n default -o yaml | base64 -d
```

2. Verify agent environment variables:
```bash
kubectl describe pod <agent-pod-name> | grep LANGFUSE
```

3. Check agent logs for LangFuse connection:
```bash
kubectl logs <agent-pod-name> | grep -i langfuse
```

### Database Issues

```bash
# Check PostgreSQL status
kubectl logs -n langfuse langfuse-postgresql-0

# Check ClickHouse cluster
kubectl logs -n langfuse langfuse-clickhouse-shard0-0

# Check disk usage if using persistence
kubectl exec -n langfuse langfuse-postgresql-0 -- df -h /bitnami/postgresql
```

### Port-Forward Issues

```bash
# Check if port is already in use
lsof -i :3000

# Use alternative port
kubectl port-forward -n langfuse svc/langfuse 3001:3000
```

## Production Considerations

### External Access

For production access without port-forwarding:

```hcl
# Option 1: LoadBalancer
langfuse_service_type = "LoadBalancer"

# Option 2: Ingress (requires ingress controller)
langfuse_ingress_enabled = true
langfuse_ingress_hostname = "langfuse.yourdomain.com"
```

### Security Best Practices

1. **Rotate API Keys Regularly**: Generate new keys quarterly
2. **Use AWS Secrets Manager**: Store LangFuse keys securely
3. **Enable RBAC**: Restrict namespace access
4. **Network Policies**: Limit traffic to LangFuse namespace
5. **Backup Strategy**:
   - Regular PostgreSQL backups
   - ClickHouse data replication
   - Persistent volume snapshots

### Resource Scaling

Monitor resource usage and scale as needed:

```bash
# Check resource usage
kubectl top pods -n langfuse

# Scale web replicas if needed
kubectl scale deployment langfuse-web -n langfuse --replicas=3
```

## Resources

- [LangFuse Documentation](https://langfuse.com/docs)
- [LangFuse Helm Chart](https://github.com/langfuse/langfuse-helm)
- [Trace Analysis Best Practices](https://langfuse.com/docs/tracing)
- [API Reference](https://langfuse.com/docs/api)
- [ClickHouse Operations](https://clickhouse.com/docs/en/operations)