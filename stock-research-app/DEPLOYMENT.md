# Azure Deployment Guide for Deep Research App

## Overview
Your app is ready to deploy to Azure. All infrastructure files have been created.

## What You Already Have ✅
- **Cosmos DB**: `<your-cosmos-account>` (stockresearch database)
- **Storage Account**: `<your-storage-account>` (for blob storage)
- **Communication Services**: `<your-acs-resource>` (for emails)
- **Resource Group**: `<your-resource-group>` in your preferred region

## What Will Be Created 🆕
- **Azure Function App**: For backend API (Python 3.11)
- **App Service Plan**: Consumption (Y1) plan for Functions
- **Static Web App**: For frontend hosting

## Deployment Steps

### Option 1: Manual Azure Portal Deployment (Recommended for First Time)

#### 1. Create Function App
```bash
# Set environment variables first
$rg = "<your-resource-group>"
$location = "<your-location>"  # e.g., eastus, westeurope
$funcName = "func-deep-research-$(Get-Random -Maximum 9999)"
$storageName = "<your-storage-account>"

# Create App Service Plan
az functionapp plan create `
  --resource-group $rg `
  --name "plan-stock-research" `
  --location $location `
  --number-of-workers 1 `
  --sku Y1 `
  --is-linux

# Create Function App
az functionapp create `
  --resource-group $rg `
  --name $funcName `
  --storage-account $storageName `
  --plan "plan-stock-research" `
  --runtime python `
  --runtime-version 3.11 `
  --functions-version 4 `
  --os-type Linux
```

#### 2. Configure Function App Settings
```bash
# Get storage connection string
$storageConn = az storage account show-connection-string `
  --name $storageName `
  --resource-group $rg `
  --query connectionString -o tsv

# Configure app settings
az functionapp config appsettings set `
  --name $funcName `
  --resource-group $rg `
  --settings `
    "AZURE_OPENAI_ENDPOINT=<YOUR_AZURE_OPENAI_ENDPOINT>" `
    "AZURE_OPENAI_API_KEY=<YOUR_AZURE_OPENAI_API_KEY>" `
    "AZURE_OPENAI_DEPLOYMENT=gpt-4o" `
    "AZURE_OPENAI_API_VERSION=2024-10-21" `
    "COSMOS_DB_URL=<YOUR_COSMOS_DB_URL>" `
    "COSMOS_DB_KEY=<YOUR_COSMOS_DB_KEY>" `
    "COSMOS_DB_NAME=stockresearch" `
    "REPORTS_CONTAINER=reports" `
    "ACS_CONNECTION_STRING=<YOUR_ACS_CONNECTION_STRING>" `
    "EMAIL_SENDER=<YOUR_ACS_EMAIL_SENDER>" `
    "BING_V7_ENDPOINT=https://api.bing.microsoft.com" `
    "APP_BASE_URL=https://$funcName.azurewebsites.net"
```

#### 3. Deploy Function App Code
```bash
cd <path-to-your-project>/stock-research-app

# Create deployment package
cd api
Compress-Archive -Path * -DestinationPath ..\functionapp.zip -Force
cd ..

# Deploy to Azure
az functionapp deployment source config-zip `
  --resource-group $rg `
  --name $funcName `
  --src functionapp.zip

# Wait for deployment
Start-Sleep -Seconds 30

# Test the deployment
$funcUrl = "https://$funcName.azurewebsites.net"
Write-Host "Function App URL: $funcUrl"
Invoke-RestMethod "$funcUrl/api/schedules"
```

#### 4. Create Static Web App
```bash
$swaName = "stapp-stock-research"

# Create Static Web App
az staticwebapp create `
  --name $swaName `
  --resource-group $rg `
  --location "eastus2" `
  --sku Free

# Get deployment token
$swaToken = az staticwebapp secrets list `
  --name $swaName `
  --resource-group $rg `
  --query "properties.apiKey" -o tsv

Write-Host "Static Web App Token: $swaToken"
Write-Host "Use this token to deploy your frontend"
```

#### 5. Deploy Frontend
```bash
cd web

# Update API endpoint in the code
# Edit src/api.ts and update BASE_URL to your Function App URL

# Install SWA CLI if not already installed
npm install -g @azure/static-web-apps-cli

# Deploy
swa deploy `
  --app-location . `
  --output-location . `
  --deployment-token $swaToken
```

### Option 2: Using Bicep Template

```bash
cd <path-to-your-project>/stock-research-app

# Set environment variables
$env:AZURE_OPENAI_API_KEY='<YOUR_AZURE_OPENAI_API_KEY>'
$env:ACS_CONNECTION_STRING='<YOUR_ACS_CONNECTION_STRING>'
$env:COSMOS_DB_KEY='<YOUR_COSMOS_DB_KEY>'

# Deploy infrastructure
az deployment group create `
  --resource-group <your-resource-group> `
  --template-file infra/main.bicep `
  --parameters infra/main.parameters.json
```

## Post-Deployment Configuration

### 1. Update CORS Settings
```bash
az functionapp cors add `
  --name $funcName `
  --resource-group $rg `
  --allowed-origins "https://$swaName.azurestaticapps.net"
```

### 2. Verify Cosmos DB Database and Containers
```bash
# Check if database exists
az cosmosdb sql database show `
  --account-name <your-cosmos-account> `
  --resource-group $rg `
  --name stockresearch

# Check if containers exist
az cosmosdb sql container show `
  --account-name <your-cosmos-account> `
  --resource-group $rg `
  --database-name stockresearch `
  --name schedules
```

### 3. Create Storage Container for Reports
```bash
az storage container create `
  --name reports `
  --account-name <your-storage-account> `
  --public-access off
```

## Testing Your Deployment

### Test Function App
```bash
# Get Function App URL
$funcUrl = az functionapp show `
  --name $funcName `
  --resource-group $rg `
  --query defaultHostName -o tsv

# Test endpoints
Invoke-RestMethod "https://$funcUrl/api/schedules"
```

### Test Static Web App
```bash
# Get Static Web App URL
$swaUrl = az staticwebapp show `
  --name $swaName `
  --resource-group $rg `
  --query defaultHostname -o tsv

Write-Host "Static Web App: https://$swaUrl"
```

## Troubleshooting

### View Function App Logs
```bash
az functionapp log tail `
  --name $funcName `
  --resource-group $rg
```

### Check Application Settings
```bash
az functionapp config appsettings list `
  --name $funcName `
  --resource-group $rg `
  --output table
```

### Restart Function App
```bash
az functionapp restart `
  --name $funcName `
  --resource-group $rg
```

## Files Created
- `/infra/main.bicep` - Infrastructure as Code
- `/infra/main.bicepparam` - Parameters file
- `/infra/abbreviations.json` - Naming conventions
- `/azure.yaml` - Azure Developer CLI configuration
- `/deploy.ps1` - Automated deployment script
- `/.azure/stock-research/.env` - Environment variables

## Next Steps
1. Execute deployment commands above
2. Test all endpoints
3. Configure GitHub Actions for CI/CD (optional)
4. Set up monitoring and alerts
5. Configure custom domain (optional)

## Estimated Costs
- **Function App (Consumption)**: Pay per execution (~$0)
- **Static Web App (Free tier)**: $0/month
- **Existing resources**: Already provisioned

Total additional cost: **~$0 - $5/month** depending on usage
