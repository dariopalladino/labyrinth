# Azure Setup Guide for Labyrinth Authentication

This guide walks you through setting up Azure Entra ID (formerly Azure AD) authentication for your Labyrinth agents and registry.

## Prerequisites

- Azure subscription with appropriate permissions
- Azure CLI installed (`az` command)
- Administrative access to create app registrations and assign permissions

## Step 1: Create Azure Entra ID App Registration

### Using Azure Portal

1. Navigate to [Azure Portal](https://portal.azure.com)
2. Go to **Azure Active Directory** > **App registrations**
3. Click **New registration**
4. Configure the application:
   - **Name**: `Labyrinth Agentic AI Solution`
   - **Supported account types**: `Accounts in this organizational directory only`
   - **Redirect URI**: Leave blank for now
5. Click **Register**

### Using Azure CLI

```bash
# Login to Azure
az login

# Create app registration
az ad app create \
    --display-name "Labyrinth Agentic AI Solution" \
    --available-to-other-tenants false

# Get the app ID (client ID) from the output
APP_ID="<your-app-id-from-output>"
```

## Step 2: Configure Authentication Settings

### Create Client Secret

#### Using Azure Portal
1. In your app registration, go to **Certificates & secrets**
2. Click **New client secret**
3. Add description: `Labyrinth Client Secret`
4. Set expiration (recommended: 24 months)
5. Click **Add**
6. **Important**: Copy the secret value immediately - you cannot retrieve it later

#### Using Azure CLI
```bash
# Create client secret
az ad app credential reset --id $APP_ID --display-name "Labyrinth Client Secret"

# Note the password from output - this is your client secret
```

### Record Important Values

From your app registration, collect these values:
- **Application (client) ID**: Found on the Overview page
- **Directory (tenant) ID**: Found on the Overview page  
- **Client Secret**: The secret value you just created

## Step 3: Configure API Permissions and Scopes

### Define Custom Scope

1. In your app registration, go to **Expose an API**
2. Click **Add a scope**
3. Configure the scope:
   - **Scope name**: `agentic_ai_solution`
   - **Who can consent**: `Admins only`
   - **Admin consent display name**: `Access Agentic AI Solution`
   - **Admin consent description**: `Allow access to Labyrinth agentic AI solution services`
   - **State**: `Enabled`
4. Click **Add scope**

### Grant API Permissions (if needed)

If your agents need to call other Azure services:

1. Go to **API permissions**
2. Click **Add a permission**
3. Select the APIs your agents will call (e.g., Microsoft Graph)
4. Choose **Application permissions** for service-to-service calls
5. Click **Add permissions**
6. Click **Grant admin consent** for your organization

## Step 4: Set Up Managed Identity (Recommended for Azure deployments)

### Create System-Assigned Managed Identity

For Azure VMs, App Service, or Container Instances:

```bash
# For Azure VM
az vm identity assign --name MyVM --resource-group MyResourceGroup

# For Azure App Service
az webapp identity assign --name MyWebApp --resource-group MyResourceGroup

# For Azure Container Instance
az container create \
    --resource-group MyResourceGroup \
    --name labyrinth-agent \
    --image myregistry/labyrinth-agent:latest \
    --assign-identity
```

### Create User-Assigned Managed Identity

```bash
# Create user-assigned managed identity
az identity create \
    --resource-group MyResourceGroup \
    --name labyrinth-managed-identity

# Assign to your resource (example for VM)
az vm identity assign \
    --identities labyrinth-managed-identity \
    --name MyVM \
    --resource-group MyResourceGroup
```

### Grant Managed Identity Access to Your App

```bash
# Get managed identity object ID
IDENTITY_OBJECT_ID=$(az identity show \
    --resource-group MyResourceGroup \
    --name labyrinth-managed-identity \
    --query principalId -o tsv)

# Assign application role (requires custom role or built-in role)
az ad app permission grant \
    --id $APP_ID \
    --api 00000003-0000-0000-c000-000000000000 \
    --scope "https://graph.microsoft.com/.default"
```

## Step 5: Configure Environment Variables

### For Client Credentials Flow

```bash
# Required variables
export LABYRINTH_AUTH_ENABLED=true
export LABYRINTH_AUTH_PROVIDER_TYPE=azure_entra_id
export LABYRINTH_AUTH_AZURE_TENANT_ID="your-tenant-id"
export LABYRINTH_AUTH_AZURE_CLIENT_ID="your-client-id"
export LABYRINTH_AUTH_AZURE_CLIENT_SECRET="your-client-secret"
export LABYRINTH_AUTH_REQUIRED_SCOPE="agentic_ai_solution"

# Optional variables
export LABYRINTH_AUTH_REQUIRE_HTTPS=true
export LABYRINTH_AUTH_TOKEN_CACHE_TTL=3600
```

### For Managed Identity Flow

```bash
# Required variables
export LABYRINTH_AUTH_ENABLED=true
export LABYRINTH_AUTH_PROVIDER_TYPE=azure_entra_id
export LABYRINTH_AUTH_AZURE_TENANT_ID="your-tenant-id"
export LABYRINTH_AUTH_USE_MANAGED_IDENTITY=true
export LABYRINTH_AUTH_REQUIRED_SCOPE="agentic_ai_solution"

# For user-assigned managed identity (optional)
export LABYRINTH_AUTH_MANAGED_IDENTITY_CLIENT_ID="user-assigned-mi-client-id"

# Optional variables
export LABYRINTH_AUTH_REQUIRE_HTTPS=true
export LABYRINTH_AUTH_TOKEN_CACHE_TTL=3600
```

## Step 6: Test Authentication Setup

### Using the Example Script

```bash
# Set your environment variables first
export LABYRINTH_AUTH_ENABLED=true
export LABYRINTH_AUTH_PROVIDER_TYPE=azure_entra_id
export LABYRINTH_AUTH_AZURE_TENANT_ID="your-tenant-id"
export LABYRINTH_AUTH_AZURE_CLIENT_ID="your-client-id"
export LABYRINTH_AUTH_AZURE_CLIENT_SECRET="your-client-secret"
export LABYRINTH_AUTH_REQUIRED_SCOPE="agentic_ai_solution"

# Run the authentication example
python examples/authenticated_agents.py
```

### Manual Testing with curl

First, get a token:

```bash
# Client credentials flow
curl -X POST "https://login.microsoftonline.com/$TENANT_ID/oauth2/v2.0/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "client_id=$CLIENT_ID" \
     -d "client_secret=$CLIENT_SECRET" \
     -d "scope=https://your-tenant.onmicrosoft.com/$APP_ID/.default" \
     -d "grant_type=client_credentials"
```

Then test with your registry:

```bash
# Use the access token from the previous response
curl -H "Authorization: Bearer $ACCESS_TOKEN" \
     "https://your-labyrinth-registry.com/health"
```

## Step 7: Deploy to Azure

### Azure App Service

```bash
# Create App Service Plan
az appservice plan create \
    --name labyrinth-plan \
    --resource-group MyResourceGroup \
    --sku B1 \
    --is-linux

# Create Web App
az webapp create \
    --resource-group MyResourceGroup \
    --plan labyrinth-plan \
    --name labyrinth-registry \
    --runtime "PYTHON|3.11" \
    --assign-identity

# Configure app settings
az webapp config appsettings set \
    --resource-group MyResourceGroup \
    --name labyrinth-registry \
    --settings \
        LABYRINTH_AUTH_ENABLED=true \
        LABYRINTH_AUTH_PROVIDER_TYPE=azure_entra_id \
        LABYRINTH_AUTH_AZURE_TENANT_ID="$TENANT_ID" \
        LABYRINTH_AUTH_USE_MANAGED_IDENTITY=true \
        LABYRINTH_AUTH_REQUIRED_SCOPE="agentic_ai_solution" \
        LABYRINTH_AUTH_REQUIRE_HTTPS=true

# Deploy your code
az webapp deployment source config \
    --resource-group MyResourceGroup \
    --name labyrinth-registry \
    --repo-url https://github.com/yourusername/labyrinth \
    --branch main \
    --manual-integration
```

### Azure Container Instances

```bash
# Create container with managed identity
az container create \
    --resource-group MyResourceGroup \
    --name labyrinth-registry \
    --image yourregistry/labyrinth:latest \
    --assign-identity \
    --environment-variables \
        LABYRINTH_AUTH_ENABLED=true \
        LABYRINTH_AUTH_PROVIDER_TYPE=azure_entra_id \
        LABYRINTH_AUTH_AZURE_TENANT_ID="$TENANT_ID" \
        LABYRINTH_AUTH_USE_MANAGED_IDENTITY=true \
        LABYRINTH_AUTH_REQUIRED_SCOPE="agentic_ai_solution" \
        LABYRINTH_AUTH_REQUIRE_HTTPS=true \
    --ports 8080 \
    --dns-name-label labyrinth-registry-unique
```

### Azure Kubernetes Service (AKS)

Create a Kubernetes deployment with Azure Workload Identity:

```yaml
# labyrinth-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: labyrinth-registry
spec:
  replicas: 3
  selector:
    matchLabels:
      app: labyrinth-registry
  template:
    metadata:
      labels:
        app: labyrinth-registry
        azure.workload.identity/use: "true"
    spec:
      serviceAccountName: labyrinth-service-account
      containers:
      - name: registry
        image: yourregistry/labyrinth:latest
        ports:
        - containerPort: 8080
        env:
        - name: LABYRINTH_AUTH_ENABLED
          value: "true"
        - name: LABYRINTH_AUTH_PROVIDER_TYPE
          value: "azure_entra_id"
        - name: LABYRINTH_AUTH_AZURE_TENANT_ID
          value: "your-tenant-id"
        - name: LABYRINTH_AUTH_USE_MANAGED_IDENTITY
          value: "true"
        - name: LABYRINTH_AUTH_REQUIRED_SCOPE
          value: "agentic_ai_solution"
        - name: LABYRINTH_AUTH_REQUIRE_HTTPS
          value: "true"
```

## Security Best Practices

### Production Checklist

- ✅ **Use HTTPS only**: Set `LABYRINTH_AUTH_REQUIRE_HTTPS=true`
- ✅ **Prefer managed identity**: Avoid client secrets in production
- ✅ **Rotate secrets regularly**: If using client credentials, rotate every 6-12 months
- ✅ **Least privilege scopes**: Only grant necessary API permissions
- ✅ **Monitor authentication**: Enable Azure AD audit logs
- ✅ **Network security**: Use private endpoints and network security groups
- ✅ **Key vault integration**: Store secrets in Azure Key Vault
- ✅ **Conditional access**: Configure conditional access policies

### Network Security

```bash
# Create private endpoint for Key Vault (if using)
az network private-endpoint create \
    --resource-group MyResourceGroup \
    --name kv-private-endpoint \
    --vnet-name MyVNet \
    --subnet private-endpoint-subnet \
    --private-connection-resource-id "/subscriptions/.../providers/Microsoft.KeyVault/vaults/MyKeyVault" \
    --group-id vault \
    --connection-name kv-connection
```

### Monitoring and Logging

Enable diagnostic settings:

```bash
# Enable App Service logs
az monitor diagnostic-settings create \
    --resource "/subscriptions/.../providers/Microsoft.Web/sites/labyrinth-registry" \
    --name labyrinth-diagnostics \
    --logs '[{"category":"AppServiceHTTPLogs","enabled":true},{"category":"AppServiceConsoleLogs","enabled":true}]' \
    --workspace "/subscriptions/.../providers/Microsoft.OperationalInsights/workspaces/MyLogAnalytics"
```

## Troubleshooting

### Common Issues

1. **"AADSTS50001: Resource not found"**
   - Check that your scope URI is correct
   - Verify app registration exists and is accessible

2. **"AADSTS65001: The user or administrator has not consented"**
   - Grant admin consent for required permissions
   - Check scope configuration

3. **"Managed identity not available"**
   - Verify managed identity is enabled on your Azure resource
   - Check that Azure Instance Metadata Service is accessible

4. **"Invalid token signature"**
   - Verify tenant ID is correct
   - Check token issuer and audience claims

### Debugging Commands

```bash
# Test managed identity token acquisition
curl -H "Metadata: true" \
     "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/"

# Decode JWT token for debugging
python -c "
import jwt
token = 'your-jwt-token-here'
print(jwt.decode(token, options={'verify_signature': False}))
"

# Check app registration details
az ad app show --id $APP_ID
```

### Support Resources

- [Azure AD Authentication Troubleshooting](https://docs.microsoft.com/en-us/azure/active-directory/develop/troubleshoot-authentication)
- [Managed Identity Troubleshooting](https://docs.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/troubleshooting)
- [Azure AD Audit Logs](https://docs.microsoft.com/en-us/azure/active-directory/reports-monitoring/concept-audit-logs)

---

## Quick Start Summary

For a rapid setup in development:

1. **Create app registration** with client secret
2. **Add custom scope** `agentic_ai_solution`  
3. **Set environment variables**:
   ```bash
   export LABYRINTH_AUTH_ENABLED=true
   export LABYRINTH_AUTH_PROVIDER_TYPE=azure_entra_id
   export LABYRINTH_AUTH_AZURE_TENANT_ID="your-tenant-id"
   export LABYRINTH_AUTH_AZURE_CLIENT_ID="your-client-id"
   export LABYRINTH_AUTH_AZURE_CLIENT_SECRET="your-client-secret"
   export LABYRINTH_AUTH_REQUIRED_SCOPE="agentic_ai_solution"
   ```
4. **Run examples**: `python examples/authenticated_agents.py`

For production, switch to managed identity and enable HTTPS!
