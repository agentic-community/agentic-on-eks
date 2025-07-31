# Authentication Guide for Agentic on EKS Demo 

This document provides a complete guide for setting up OAuth 2.0 authentication with Okta for the Agentic EKS Demo project, covering both UI user authentication and agent-to-agent (A2A) communication.

## Overview

The system implements a comprehensive two-tier authentication architecture:

1. **UI Authentication**: Users authenticate via Okta to access the Streamlit chat interface
2. **Agent-to-Agent (A2A) Authentication**: Backend agents authenticate with each other using OAuth 2.0 Client Credentials flow

### Key Features
- Follows A2A security requirements outlined in the A2A protocol
- Uses OAuth 2.0 client credentials flow for machine-to-machine authentication
- Provides proper scope-based authorization
- Makes authentication information available in agent cards
- Validates tokens using industry-standard JWT verification

## Prerequisites

Before setting up OAuth with Okta, you'll need:

1. An Okta developer account (free tier available at [developer.okta.com](https://developer.okta.com))
2. Administrative access to your Okta account
3. Python 3.8 or higher
4. Kubernetes cluster with appropriate RBAC
5. The following Python packages:
   - `httpx`
   - `python-jose[cryptography]`
   - `starlette`

## Okta Configuration

### Step 1: Create an Okta Developer Account

1. Sign up at [developer.okta.com](https://developer.okta.com)
2. Create your organization (e.g., `trial-XXXXXXX.okta.com`)
3. Verify your email and access the Admin Console

### Step 2: Set Up Authorization Server

1. Log in to your Okta Admin Console
2. Navigate to **Security** > **API**
3. Select the **Authorization Servers** tab
4. Click **Add Authorization Server**
5. Fill in the details:
   - **Name**: `A2A-AuthServer`
   - **Description**: `Authorization server for agent-to-agent communication`
   - **Audience**: `api://a2a-agents`
   - **Issuer**: Use the default value
6. Click **Save**

### Step 3: Create Scopes

1. Select your newly created authorization server
2. Go to the **Scopes** tab
3. Click **Add Scope**
4. Create the following scope:
   - `agent.access`: Access to agent API for A2A communication

### Step 4: Create Access Policies

1. Go to the **Access Policies** tab
2. Click **Add Policy**
3. Fill in the details:
   - **Name**: `A2A-Machine-to-Machine`
   - **Description**: `Policy for machine-to-machine communication`
   - **Assign to**: Select **All clients**
4. Click **Create Policy**
5. Add a rule to this policy:
   - Click **Add Rule**
   - **Rule Name**: `Client Credentials`
   - **Grant type**: Check **Client Credentials**
   - **Scopes**: Select the scope you created (`agent.access`)
   - **Token Lifetime**: Set to desired value (default: 1 hour)
6. Click **Create Rule**

## Application Setup

### Agent-UI-App (UI Authentication)

#### Purpose
Handles user authentication for the Streamlit UI interface.

#### Configuration Steps
1. **Create Application**:
   - Applications → Create App Integration
   - OIDC - OpenID Connect → Web Application
   - Name: `Agent-UI-App`

2. **General Settings**:
   - **Grant types**: ✅ Authorization Code, ✅ Refresh Token
   - **Client authentication**: ✅ Client secret
   - **Sign-in redirect URIs**: 
     - `http://localhost:8501` (for port-forward testing)
     - `https://your-loadbalancer-url` (for production)
   - **Controlled access**: Allow everyone in your organization

3. **Sign On Settings**:
   - **OpenID Connect ID Token**: Enabled
   - **Groups claim type**: Expression
   - **Groups claim name**: `groups`

4. **Credentials**:
   - Note the **Client ID** (used in deployment)
   - Note the **Client Secret** (used in deployment)

### All-Agents-App (A2A Authentication)

#### Purpose
Handles machine-to-machine authentication between backend agents.

#### Configuration Steps
1. **Create Application**:
   - Applications → Create App Integration
   - API Services → Machine-to-Machine
   - Name: `All-Agents-App`

2. **General Settings**:
   - **Grant types**: ✅ Client Credentials
   - **Client authentication**: ✅ Client secret

3. **Credentials**:
   - Note the **Client ID** (used by Admin Agent)
   - Note the **Client Secret** (used by Admin Agent)

4. **Scope Assignment**:
   - Go to the **Okta API Scopes** tab
   - Grant the application access to the `agent.access` scope

## Authentication Flows

### UI Authentication Flow

1. **User Access**: User visits UI application
2. **Login Required**: UI redirects to Okta login page
3. **Okta Authentication**: User enters credentials
4. **Authorization Code**: Okta redirects back with auth code
5. **Token Exchange**: UI exchanges code for ID token and access token
6. **Session Creation**: UI creates authenticated session
7. **Chat Access**: User can now interact with agents

### A2A Authentication Flow

1. **Service Request**: Admin Agent needs to call HR/Finance agent
2. **Token Acquisition**: Admin Agent requests token from A2A-AuthServer
3. **Client Credentials**: Uses All-Agents-App credentials
4. **Access Token**: Receives JWT token with appropriate scopes
5. **Authenticated Request**: Includes token in Authorization header
6. **Token Validation**: Target agent validates token against Okta
7. **Service Response**: Returns authenticated response

## Deployment Configuration

### OAuth Configuration During Deployment

The current implementation uses interactive prompts during deployment. Each agent's `deploy.sh` script will prompt for the necessary OAuth credentials:

**Admin Agent Deployment** will prompt for:
- `OKTA_DOMAIN` (e.g., trial-xxxxxxx.okta.com)
- `OKTA_AUTH_SERVER_ID` (your authorization server ID)
- `OKTA_CLIENT_ID` (from All-Agents-App)
- `OKTA_CLIENT_SECRET` (from All-Agents-App)

**HR Agent Deployment** will prompt for:
- `OKTA_DOMAIN` (e.g., trial-xxxxxxx.okta.com)
- `OKTA_AUTH_SERVER_ID` (your authorization server ID)

**Finance Agent Deployment** will prompt for:
- `OKTA_DOMAIN` (e.g., trial-xxxxxxx.okta.com)
- `OKTA_AUTH_SERVER_ID` (your authorization server ID)

**UI App Deployment** will prompt for:
- `OKTA_DOMAIN` (e.g., trial-xxxxxxx.okta.com)
- `OKTA_CLIENT_ID` (from Agent-UI-App)
- `OKTA_CLIENT_SECRET` (from Agent-UI-App)

### Kubernetes Integration

#### Secret Management
The system uses Kubernetes Secrets to securely store Okta credentials:

```yaml
# Admin Agent OAuth Secret
apiVersion: v1
kind: Secret
metadata:
  name: admin-agent-oauth-secrets
  namespace: default
type: Opaque
data:
  OKTA_DOMAIN: BASE64_ENCODED_DOMAIN
  OKTA_AUTH_SERVER_ID: BASE64_ENCODED_AUTH_SERVER_ID
  OKTA_CLIENT_ID: BASE64_ENCODED_CLIENT_ID
  OKTA_CLIENT_SECRET: BASE64_ENCODED_CLIENT_SECRET
  OKTA_SCOPE: # base64 for "agent.access"
  OKTA_AUDIENCE: # base64 for "api://a2a-agents"
```

```yaml
# UI OKTA credentials stored in Secret
apiVersion: v1
kind: Secret
metadata:
  name: ui-app-okta-secrets
stringData:
  OKTA_DOMAIN: "your-domain.okta.com"
  OKTA_CLIENT_ID: "your-ui-client-id"
  OKTA_CLIENT_SECRET: "your-ui-client-secret"
```

#### Configuration Management
Non-sensitive configuration stored in ConfigMap:

```yaml
# UI configuration in ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: ui-app-config
data:
  OKTA_REDIRECT_URI: "http://localhost:8501"
  OKTA_SCOPE: "openid profile email"
  DEMO_MODE: "false"
```

## Implementation Details

### 1. OAuth Client (`common/utils/oauth_auth.py`)

The OAuth client is responsible for acquiring tokens from Okta:

```python
# Example usage
from common.utils.oauth_auth import OAuthClient, OAuthConfig

config = OAuthConfig(
    domain="your-okta-domain",
    client_id="your-client-id",
    client_secret="your-client-secret",
    scope="agent.access",
    audience="api://a2a-agents",
    token_endpoint="https://<domain>/oauth2/your-auth-server-id/v1/token"
)

client = OAuthClient(config)
token = await client.get_token()
```

### 2. OAuth Middleware (`common/server/oauth_middleware.py`)

The middleware validates incoming requests:

```python
# Example usage in server.py
from common.server.oauth_middleware import configure_oauth_middleware

# Configure the app with OAuth middleware
app = configure_oauth_middleware(app, public_paths=["/.well-known/agent.json"])
```

### 3. Key Security Features

- **Public paths exempted**: `/.well-known/agent.json`, `/docs`, `/health`
- **Token validation**: JWT signature validation using Okta's public keys
- **Scope validation**: Requires `agent.access` scope for A2A communication
- **Proper error responses**: 401 for invalid/missing tokens, 403 for insufficient scopes

## Deployment Steps

### Prerequisites
- Okta Developer account configured as above
- Kubernetes cluster with appropriate RBAC
- ECR repository for container images

### Step-by-Step Deployment

1. **Deploy Admin Agent**:
   ```bash
   cd agents/admin
   ./deploy.sh
   ```

2. **Deploy HR Agent**:
   ```bash
   cd agents/hr
   ./deploy.sh
   ```

3. **Deploy Finance Agent**:
   ```bash
   cd agents/finance
   ./deploy.sh
   ```

4. **Deploy UI application**:
   ```bash
   cd ui
   ./deploy.sh
   ```

5. **Access application**:
   ```bash
   kubectl port-forward svc/ui-app-service 8501:80
   # Visit: http://localhost:8501
   ```

## Testing

### UI Authentication Test
1. Access `http://localhost:8501`
2. Click "Login with Okta"
3. Enter Okta credentials
4. Verify redirect to chat interface
5. Confirm user info displayed in sidebar

### End-to-End Agent Communication Test
1. **HR Query**: "What is the name of employee EMP0002?"
2. **Finance Query**: "What is the annual salary of EMP0003?"
3. **Verify**: Responses from appropriate backend agents

### Demo Mode
For testing without Okta authentication:
```bash
kubectl patch configmap ui-app-config -p '{"data":{"DEMO_MODE":"true"}}'
kubectl rollout restart deployment/ui-app-deployment
```

## Troubleshooting

### Common Issues

#### Token Acquisition Failures
- Check that your client ID and client secret are correct
- Verify that the All-Agents-App has been granted the `agent.access` scope
- Ensure the authorization server is properly configured

#### Token Validation Failures
- Check that the Issuer URL is correct
- Verify that the audience matches what's configured in Okta (`api://a2a-agents`)
- Ensure the token is not expired
- Look for scopes in both `scope` and `scp` fields

#### Scope Validation Issues
The current implementation requires the `agent.access` scope. Ensure:
- The All-Agents-App has been granted this scope in Okta
- The authorization server policy includes this scope
- The token contains this scope in either `scope` or `scp` fields

### Debugging Commands

```bash
# Check UI pod logs
kubectl logs -l app=ui-app -f

# Check agent OAuth logs
kubectl logs -l app=admin-agent -f  # Token acquisition
kubectl logs -l app=hr-agent -f     # Token validation
kubectl logs -l app=finance-agent -f # Token validation

# Check secrets
kubectl get secret ui-app-okta-secrets -o yaml
kubectl get secret admin-agent-oauth-secrets -o yaml
kubectl get secret hr-agent-oauth-secrets -o yaml
kubectl get secret finance-agent-oauth-secrets -o yaml

# Check configuration
kubectl get configmap ui-app-config -o yaml

# Test pod connectivity
kubectl exec -it <ui-pod> -- wget -qO- http://admin-agent-service:8080/.well-known/agent.json

# Test OAuth validation (should fail without token)
kubectl exec -it <admin-pod> -- curl -X POST http://hr-agent-service/ -H "Content-Type: application/json"

# Test OAuth validation (should work with valid token)
kubectl exec -it <admin-pod> -- curl -X POST http://hr-agent-service/ -H "Authorization: Bearer <valid-token>"
```

## Security Considerations

### Credentials Management
- ✅ **No hardcoded secrets**: All credentials via environment variables or prompts
- ✅ **Kubernetes Secrets**: Sensitive data encrypted at rest
- ✅ **Session security**: Proper session management with Okta tokens
- ✅ **Token validation**: All A2A calls validate OAuth tokens

### Network Security
- ✅ **Internal LoadBalancer**: UI not exposed to internet
- ✅ **Cluster networking**: All agent communication within cluster

### Additional Security Best Practices
- **Secret Management**: Store client secrets securely in Kubernetes Secrets or environment variables
- **Token Lifetimes**: Configure appropriate token lifetimes (shorter is more secure)
- **Scope Design**: The `agent.access` scope provides broad access - consider more granular scopes for production
- **Network Security**: Use TLS for all communications
- **Audit Logging**: Monitor and log authentication events

## Implementation Summary

### ✅ OAuth A2A Flow Successfully Implemented

The system now features a complete OAuth 2.0 authentication implementation with the following components:

#### Complete Security Flow
- **UI → Okta**: User authentication with OAuth2 authorization code flow
- **Admin Agent → Okta**: Client credentials flow to get access tokens  
- **Admin Agent → HR/Finance**: Bearer token authentication via A2A protocol
- **HR/Finance Agents**: JWT token validation using Okta JWKS

#### Key Components Implemented

1. **OAuth Middleware** (`common/server/oauth_middleware.py`)
   - HTTP request interception and Bearer token extraction
   - JWT token validation against Okta JWKS endpoints
   - Scope-based authorization with proper error responses

2. **JWT Validation Utilities** (`common/utils/oauth_auth.py`)
   - Okta configuration management from environment variables
   - JWT signature validation using Okta's public keys  
   - Token claims extraction and validation

3. **Agent Integration**
   - OAuth middleware enabled on HR and Finance agents
   - Token validation with `agent.access` scope requirement
   - Admin Agent OAuth client for A2A communication

#### Test Results
- ✅ **Valid OAuth credentials**: Admin Agent gets tokens, HR/Finance accept requests
- ❌ **Invalid OAuth credentials**: Admin Agent fails to get tokens, HR/Finance reject requests with 401
- ✅ **Public endpoints**: Accessible without authentication (agent discovery)
- ✅ **Protected endpoints**: Require valid Bearer tokens

#### Architecture Benefits
- **Separation of concerns**: OAuth logic separated from HTTP handling
- **Framework independence**: Could switch OAuth providers easily
- **Reusability**: OAuth utilities can be used in different contexts
- **Testability**: OAuth logic can be tested independently

The OAuth authentication implementation provides comprehensive security with industry-standard OAuth2 and JWT validation, making the system production-ready for enterprise deployment.