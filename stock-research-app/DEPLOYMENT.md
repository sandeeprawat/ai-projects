# Deployment Guide - Stock Research Application

This guide provides instructions for deploying the Stock Research Application to Azure using Azure Developer CLI (azd) and VS Code.

## Prerequisites

Before deploying, ensure you have the following installed:

- **Azure Developer CLI (azd)**: [Install azd](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd)
- **Azure CLI**: [Install Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)
- **Python 3.10+**: [Install Python](https://www.python.org/downloads/)
- **Node.js 18+**: [Install Node.js](https://nodejs.org/)
- **Azure Functions Core Tools v4**: [Install Core Tools](https://learn.microsoft.com/azure/azure-functions/functions-run-local)
- **VS Code** (optional but recommended): [Install VS Code](https://code.visualstudio.com/)
- **Azure Subscription**: You need an active Azure subscription

## Azure Resources Required

The deployment will provision the following Azure resources:

- **Azure Static Web App** - Hosts the React frontend
- **Azure Functions App** - Runs the Python backend with Durable Functions
- **Azure Cosmos DB** - NoSQL database for schedules, runs, and reports
- **Azure Storage Account** - Blob storage for report files
- **Azure OpenAI Service** - AI model for report generation
- **Azure AI Services (Bing Search v7)** - Web search capabilities
- **Azure Communication Services** - Email delivery
- **Azure Key Vault** - Secrets management
- **Application Insights** - Monitoring and telemetry
- **Log Analytics Workspace** - Centralized logging

## Quick Start Deployment

### Option 1: Deploy with Azure Developer CLI (azd)

1. **Navigate to the project directory:**
   ```bash
   cd stock-research-app
   ```

2. **Initialize azd (first time only):**
   ```bash
   azd init
   ```
   
   Follow the prompts to configure your environment.

3. **Login to Azure:**
   ```bash
   azd auth login
   ```

4. **Provision and Deploy:**
   ```bash
   azd up
   ```
   
   This single command will:
   - Provision all Azure resources
   - Deploy the API (Azure Functions)
   - Deploy the web app (Static Web App)
   - Configure necessary environment variables

5. **Note the output values** - azd will display important URLs and resource names.

### Option 2: Deploy with VS Code

1. **Open the project in VS Code:**
   ```bash
   code .
   ```

2. **Install the Azure Developer CLI extension** for VS Code (if not already installed)

3. **Use the Command Palette (Ctrl+Shift+P or Cmd+Shift+P):**
   - Type: `Azure Developer: Up`
   - Select the command and follow the prompts

4. **The extension will guide you through:**
   - Signing in to Azure
   - Selecting a subscription
   - Choosing a location
   - Provisioning resources
   - Deploying the application

## Manual Deployment Steps

If you prefer more control, you can deploy manually:

### 1. Provision Infrastructure

```bash
# Login to Azure
az login

# Set your subscription
az account set --subscription <subscription-id>

# Create a resource group
az group create --name rg-stock-research --location eastus

# Deploy Bicep template
az deployment sub create \
  --location eastus \
  --template-file infra/main.bicep \
  --parameters environmentName=stock-research \
               location=eastus \
               principalId=$(az ad signed-in-user show --query id -o tsv)
```

### 2. Deploy Function App

```bash
# Navigate to API directory
cd api

# Install dependencies
pip install -r requirements.txt

# Deploy to Azure Functions
func azure functionapp publish <function-app-name>
```

### 3. Deploy Static Web App

```bash
# Navigate to web directory
cd web

# Install dependencies
npm install

# Build the application
npm run build

# Deploy to Static Web App (using SWA CLI or GitHub Actions)
npx @azure/static-web-apps-cli deploy \
  --app-location ./dist \
  --deployment-token <your-deployment-token>
```

## Post-Deployment Configuration

After deployment, you need to configure a few additional settings:

### 1. Configure Azure Communication Services Email

1. Navigate to the Azure Portal
2. Find your Azure Communication Services Email resource
3. Set up an email domain or use the free Azure-managed domain
4. Update the `EMAIL_SENDER_ADDRESS` environment variable in your Function App

### 2. Configure Authentication Providers (Static Web App)

1. Go to your Static Web App in the Azure Portal
2. Navigate to **Settings** > **Authentication**
3. Add authentication providers:
   - **Microsoft** (Azure AD)
   - **Google** (OAuth)
4. Configure redirect URLs and client secrets

### 3. Verify Environment Variables

Check that all environment variables are set correctly in the Function App:

```bash
# List function app settings
az functionapp config appsettings list \
  --name <function-app-name> \
  --resource-group <resource-group-name>
```

Required settings:
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_DEPLOYMENT`
- `AZURE_OPENAI_API_VERSION`
- `BING_V7_ENDPOINT`
- `COSMOS_DB_URL`
- `COSMOS_DB_NAME`
- `REPORTS_CONTAINER`
- `ACS_CONNECTION_STRING`
- `EMAIL_SENDER`
- `APP_BASE_URL`

## Local Development Setup

### 1. API (Azure Functions)

```bash
cd stock-research-app/api

# Create local settings file
cp local.settings.json.example local.settings.json

# Edit local.settings.json with your Azure resource values
# You can get these from the Azure Portal or from azd environment

# Install dependencies
pip install -r requirements.txt

# Start Azurite (local storage emulator)
azurite --silent --location .data/azurite --debug .data/azurite/debug.log

# Start Functions runtime
func start
```

### 2. Web (React Frontend)

```bash
cd stock-research-app/web

# Install dependencies
npm install

# Start development server
npm run dev
```

The web app will be available at http://localhost:5173 and will connect to the Functions API at http://localhost:7071.

## VS Code Quick Start

For the fastest local development experience:

1. **Open in VS Code:**
   ```bash
   code stock-research-app
   ```

2. **Use the Run and Debug panel (Ctrl+Shift+D):**
   - Select "Attach to Python Functions"
   - Click the green play button

3. **Use Tasks for common operations:**
   - `Ctrl+Shift+P` > "Tasks: Run Task"
   - Select from:
     - `func: host start` - Start Functions
     - `web: start (vite dev)` - Start web dev server
     - `Start Azurite` - Start storage emulator

## Environment Variables

Create a `.env` file in the root directory (not committed to git):

```env
AZURE_ENV_NAME=stock-research
AZURE_LOCATION=eastus
AZURE_SUBSCRIPTION_ID=<your-subscription-id>

# Optional: Override defaults
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_MODEL_NAME=gpt-4o-mini
AZURE_OPENAI_MODEL_VERSION=2024-07-18
EMAIL_SENDER_ADDRESS=noreply@yourdomain.com
EMAIL_DOMAIN=yourdomain.com
```

## Troubleshooting

### Common Issues

1. **"azd: command not found"**
   - Install Azure Developer CLI: https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd

2. **Deployment fails with authentication error**
   - Run `azd auth login` or `az login`
   - Ensure you have appropriate permissions in your Azure subscription

3. **Function App deployment fails**
   - Check that Python 3.10+ is installed
   - Verify all dependencies in requirements.txt are available
   - Check Function App logs in Azure Portal

4. **Static Web App build fails**
   - Ensure Node.js 18+ is installed
   - Run `npm install` in the web directory
   - Check for TypeScript errors with `npm run build`

5. **Cannot connect to local Functions**
   - Ensure Azurite is running
   - Check that local.settings.json exists and is configured
   - Verify port 7071 is not in use

### Getting Help

- Check the [Azure Functions documentation](https://learn.microsoft.com/azure/azure-functions/)
- Review [Azure Developer CLI documentation](https://learn.microsoft.com/azure/developer/azure-developer-cli/)
- Check [Application Insights](https://portal.azure.com) for runtime errors

## Monitoring and Observability

After deployment, monitor your application:

1. **Application Insights Dashboard**
   - Navigate to your Application Insights resource in Azure Portal
   - View live metrics, failures, and performance

2. **Function App Logs**
   - Use Azure Portal > Function App > Log Stream
   - Or use: `func azure functionapp logstream <function-app-name>`

3. **Durable Functions Orchestrations**
   - Check orchestration status in Durable Functions monitor
   - Available in Azure Portal > Function App > Durable Functions

## Clean Up

To delete all deployed resources:

```bash
# Using azd
azd down

# Or manually delete the resource group
az group delete --name rg-stock-research --yes
```

## Next Steps

1. Configure authentication providers in Static Web App
2. Set up email domain in Azure Communication Services
3. Test the application end-to-end
4. Set up CI/CD with GitHub Actions (generated by azd)
5. Configure custom domain and SSL certificate
6. Set up monitoring alerts in Application Insights

## Security Best Practices

- All secrets are stored in Azure Key Vault
- Managed Identity is used for authentication between services
- HTTPS is enforced for all endpoints
- Public blob access is disabled
- RBAC is used instead of access keys where possible
- Soft delete is enabled for Key Vault

## Cost Optimization

The default deployment uses cost-effective SKUs:

- **Cosmos DB**: Serverless mode
- **Functions**: Consumption (Y1) plan
- **Static Web App**: Free tier
- **Storage**: Standard LRS
- **Application Insights**: Pay-as-you-go

For production, consider upgrading to:
- Cosmos DB with provisioned throughput
- Functions Premium plan for better performance
- Static Web App Standard tier for custom domains and advanced features

## Support

For issues specific to this application, please open an issue in the GitHub repository.

For Azure service issues, contact Azure Support through the Azure Portal.
