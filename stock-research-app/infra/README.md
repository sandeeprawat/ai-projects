# Infrastructure as Code - Stock Research Application

This directory contains Azure Bicep templates for provisioning the Stock Research Application infrastructure.

## Overview

The infrastructure is defined using Azure Bicep, a domain-specific language (DSL) for deploying Azure resources. The templates follow a modular approach with reusable components.

## Structure

```
infra/
├── main.bicep                    # Main entry point - orchestrates all resources
├── main.parameters.json          # Parameter file for main template
├── abbreviations.json            # Resource naming abbreviations
└── core/                         # Reusable modules
    ├── database/
    │   └── cosmos-account.bicep  # Cosmos DB account and containers
    ├── storage/
    │   └── storage-account.bicep # Storage account and blob containers
    ├── monitor/
    │   └── monitoring.bicep      # Application Insights and Log Analytics
    ├── security/
    │   ├── keyvault.bicep        # Key Vault configuration
    │   ├── keyvault-secrets.bicep # Key Vault secrets
    │   └── role.bicep            # RBAC role assignments
    ├── ai/
    │   └── cognitiveservices.bicep # Azure OpenAI and Bing Search
    ├── communication/
    │   └── communication-services.bicep # Azure Communication Services (Email)
    └── host/
        ├── appserviceplan.bicep  # App Service Plan for Functions
        ├── functions.bicep       # Azure Functions App
        └── staticwebapp.bicep    # Static Web App for frontend
```

## Resources Provisioned

### Core Services
- **Resource Group** - Container for all resources
- **Azure Static Web App** - Hosts the React frontend
- **Azure Functions App** - Runs the Python backend
- **App Service Plan** - Consumption (Y1) plan for Functions

### Data & Storage
- **Cosmos DB** - Serverless NoSQL database
  - Database: `stockresearch`
  - Containers: `schedules`, `runs`, `reports`
- **Azure Storage Account** - Blob storage for report files
  - Container: `reports`

### AI & Communication
- **Azure OpenAI Service** - GPT-4o-mini for report generation
- **Azure AI Services** - Bing Search v7 for web research
- **Azure Communication Services** - Email delivery

### Security & Monitoring
- **Key Vault** - Stores API keys and secrets
- **Managed Identity** - Function App uses system-assigned identity
- **RBAC Roles** - Least-privilege access to resources
- **Application Insights** - Application monitoring and telemetry
- **Log Analytics** - Centralized logging

## Deployment

### Prerequisites

- Azure CLI installed and authenticated
- Appropriate permissions in Azure subscription
- Azure Developer CLI (azd) - recommended

### Using Azure Developer CLI (Recommended)

```bash
# Navigate to stock-research-app directory
cd stock-research-app

# Login to Azure
azd auth login

# Provision resources
azd provision

# Or provision and deploy in one command
azd up
```

### Using Azure CLI

```bash
# Set variables
LOCATION="eastus"
ENV_NAME="stock-research"
SUBSCRIPTION_ID="your-subscription-id"

# Login
az login
az account set --subscription $SUBSCRIPTION_ID

# Get your user principal ID
PRINCIPAL_ID=$(az ad signed-in-user show --query id -o tsv)

# Deploy at subscription scope
az deployment sub create \
  --location $LOCATION \
  --template-file infra/main.bicep \
  --parameters environmentName=$ENV_NAME \
               location=$LOCATION \
               principalId=$PRINCIPAL_ID
```

### Using Bicep CLI Directly

```bash
# Validate template
az bicep build --file infra/main.bicep

# Deploy
az deployment sub create \
  --location eastus \
  --template-file infra/main.bicep \
  --parameters @infra/main.parameters.json
```

## Parameters

The following parameters can be customized in `main.parameters.json` or via command line:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `environmentName` | Environment name (e.g., dev, staging, prod) | Required |
| `location` | Azure region for resources | Required |
| `principalId` | User/App principal ID for Key Vault access | Required |
| `openAiDeploymentName` | Azure OpenAI deployment name | gpt-4o-mini |
| `openAiModelName` | OpenAI model to deploy | gpt-4o-mini |
| `openAiModelVersion` | OpenAI model version | 2024-07-18 |
| `openAiSkuName` | OpenAI service SKU | S0 |
| `emailSenderAddress` | Email sender address | (empty) |
| `emailDomain` | Email domain for ACS | (empty) |

## Environment Variables

The templates use environment variable substitution in parameters. Set these before deployment:

```bash
# Required
export AZURE_ENV_NAME="stock-research"
export AZURE_LOCATION="eastus"
export AZURE_PRINCIPAL_ID=$(az ad signed-in-user show --query id -o tsv)

# Optional
export AZURE_OPENAI_DEPLOYMENT="gpt-4o-mini"
export AZURE_OPENAI_MODEL_NAME="gpt-4o-mini"
export AZURE_OPENAI_MODEL_VERSION="2024-07-18"
export EMAIL_SENDER_ADDRESS="noreply@yourdomain.com"
export EMAIL_DOMAIN="yourdomain.com"
```

## Outputs

After deployment, the following outputs are available:

| Output | Description |
|--------|-------------|
| `AZURE_RESOURCE_GROUP` | Resource group name |
| `FUNCTION_APP_NAME` | Function App name |
| `FUNCTION_APP_URL` | Function App URL |
| `STATIC_WEB_APP_NAME` | Static Web App name |
| `STATIC_WEB_APP_URL` | Static Web App URL |
| `COSMOS_DB_URL` | Cosmos DB endpoint |
| `STORAGE_ACCOUNT_NAME` | Storage account name |
| `KEY_VAULT_NAME` | Key Vault name |
| `APPLICATION_INSIGHTS_NAME` | App Insights name |

Access outputs with:

```bash
# Using azd
azd env get-values

# Using Azure CLI
az deployment sub show \
  --name <deployment-name> \
  --query properties.outputs
```

## Security

### Managed Identity & RBAC

The Function App uses a system-assigned managed identity with the following roles:

- **Cosmos DB Built-in Data Contributor** - Read/write to Cosmos DB
- **Storage Blob Data Contributor** - Read/write to blob storage
- **Key Vault Secrets User** - Read secrets from Key Vault

No access keys are stored in application configuration.

### Secrets Management

API keys are stored in Key Vault:
- `AZURE-OPENAI-API-KEY` - Azure OpenAI access key
- `BING-V7-KEY` - Bing Search API key
- `COSMOS-DB-KEY` - Cosmos DB key (for backward compatibility)

The Function App accesses these using managed identity.

### Network Security

- HTTPS is enforced on all endpoints
- Public blob access is disabled
- Key Vault has soft delete enabled
- TLS 1.2 is the minimum version for storage

## Cost Optimization

The default configuration uses cost-effective SKUs:

| Resource | SKU/Tier | Estimated Cost* |
|----------|----------|-----------------|
| Functions | Consumption (Y1) | Pay per execution |
| Cosmos DB | Serverless | Pay per RU consumed |
| Storage | Standard LRS | ~$0.02/GB/month |
| Static Web App | Free | $0 |
| App Insights | Pay-as-you-go | First 5GB free |
| Key Vault | Standard | ~$0.03/10k ops |
| OpenAI | S0 | Pay per token |
| Bing Search | S1 | ~$7/1000 queries |

*Estimates as of 2024. Check Azure pricing for current rates.

### Cost Management Tips

1. **Development Environment:**
   - Use Cosmos DB serverless
   - Use Functions consumption plan
   - Clean up resources when not in use (`azd down`)

2. **Production Environment:**
   - Consider Cosmos DB provisioned throughput for predictable workloads
   - Use Functions Premium plan for better performance
   - Implement proper monitoring and alerts

## Customization

### Adding Resources

To add a new resource:

1. Create a new module in `core/` directory
2. Reference it in `main.bicep`
3. Add any required parameters
4. Update outputs as needed

Example:

```bicep
module redis './core/cache/redis.bicep' = {
  name: 'redis'
  scope: rg
  params: {
    name: '${abbrs.cacheRedis}${resourceToken}'
    location: location
    tags: tags
  }
}
```

### Multiple Environments

Deploy to multiple environments:

```bash
# Development
azd env new dev
azd up

# Staging
azd env new staging
azd up

# Production
azd env new prod
azd up
```

Each environment gets its own resource group and configuration.

## Validation

Before deploying, validate the templates:

```bash
# Validate Bicep syntax
az bicep build --file infra/main.bicep

# Validate deployment
az deployment sub validate \
  --location eastus \
  --template-file infra/main.bicep \
  --parameters @infra/main.parameters.json

# What-if analysis (preview changes)
az deployment sub what-if \
  --location eastus \
  --template-file infra/main.bicep \
  --parameters @infra/main.parameters.json
```

## Troubleshooting

### Common Issues

1. **"Principal does not have access to secrets"**
   - Ensure `principalId` parameter is set correctly
   - Check RBAC role assignments in Key Vault

2. **"Location not available for resource"**
   - Some resources (like OpenAI) may not be available in all regions
   - Try a different location (e.g., eastus, westeurope)

3. **"Quota exceeded"**
   - Check subscription quotas
   - Request quota increase if needed

4. **"Deployment failed with conflict"**
   - Resource names must be globally unique
   - The template uses a unique suffix based on subscription ID

### Debug Deployment

```bash
# View deployment details
az deployment sub show \
  --name <deployment-name> \
  --query properties.error

# View deployment operations
az deployment sub operation list \
  --name <deployment-name>

# View activity log
az monitor activity-log list \
  --resource-group <resource-group> \
  --max-events 10
```

## Clean Up

Delete all resources:

```bash
# Using azd
azd down

# Using Azure CLI
az group delete --name rg-<env-name> --yes
```

## References

- [Azure Bicep Documentation](https://learn.microsoft.com/azure/azure-resource-manager/bicep/)
- [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/)
- [Azure Resource Naming Conventions](https://learn.microsoft.com/azure/cloud-adoption-framework/ready/azure-best-practices/resource-naming)
- [Azure Well-Architected Framework](https://learn.microsoft.com/azure/architecture/framework/)

## Contributing

When adding new infrastructure:

1. Follow the modular pattern
2. Use consistent naming (see `abbreviations.json`)
3. Document all parameters
4. Add appropriate tags
5. Include outputs for important values
6. Test deployment in a dev environment first

## Support

For infrastructure issues:

1. Check the troubleshooting section above
2. Review Azure Portal deployment logs
3. Check Application Insights for runtime issues
4. Open an issue in the GitHub repository
