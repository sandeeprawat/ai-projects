# Quick Start Guide - VS Code Deployment

This guide shows you how to quickly deploy the Stock Research Application from VS Code.

## Prerequisites

1. Install the following VS Code extensions:
   - **Azure Developer CLI** (ms-azuretools.azure-dev)
   - **Azure Functions** (ms-azuretools.vscode-azurefunctions)
   - **Azure Resources** (ms-azuretools.vscode-azureresourcegroups)
   - **Bicep** (ms-azuretools.vscode-bicep)

2. Install required tools:
   - Azure Developer CLI (azd)
   - Azure CLI (az)
   - Python 3.10+
   - Node.js 18+
   - Azure Functions Core Tools v4

## Quick Deployment Steps

### 1. Open in VS Code

```bash
code stock-research-app
```

### 2. Deploy Using Tasks

Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac) and select **Tasks: Run Task**, then choose:

#### First-time Deployment:
1. **azd: up (provision + deploy)** - Provisions all Azure resources and deploys the application

#### Subsequent Deployments:
1. **azd: deploy** - Only deploys code changes (faster)

### 3. Other Useful Tasks

Available tasks in VS Code:

**Deployment Tasks:**
- `azd: up (provision + deploy)` - Full deployment
- `azd: provision` - Only provision infrastructure
- `azd: deploy` - Only deploy code
- `azd: down (delete resources)` - Delete all Azure resources

**Infrastructure Tasks:**
- `bicep: validate infrastructure` - Validate Bicep templates

**Build Tasks:**
- `web: build` - Build React frontend
- `api: install dependencies` - Install Python dependencies

**Local Development Tasks:**
- `func: host start` - Start Azure Functions locally
- `web: start (vite dev)` - Start React dev server
- `Start Azurite` - Start local storage emulator

## Using the Command Palette

### Deploy with Azure Developer CLI Extension

1. Press `Ctrl+Shift+P` (or `Cmd+Shift+P`)
2. Type: `Azure Developer: Up`
3. Follow the prompts:
   - Sign in to Azure (if not already signed in)
   - Select subscription
   - Choose location (e.g., East US)
   - Enter environment name (e.g., "stock-research-dev")

The extension will:
- Provision all Azure resources
- Deploy the Function App (API)
- Deploy the Static Web App (frontend)
- Display deployment results

## Local Development

### Start All Services

1. **Start Storage Emulator:**
   - Press `Ctrl+Shift+P` > **Tasks: Run Task** > **Start Azurite**

2. **Start Function App:**
   - Press `F5` or use **Run and Debug** panel
   - Select "Attach to Python Functions"

3. **Start Web Frontend:**
   - Press `Ctrl+Shift+P` > **Tasks: Run Task** > **web: start (vite dev)**

### Access Local Application

- **Frontend:** http://localhost:5174
- **API:** http://localhost:7071
- **API Documentation:** http://localhost:7071/api/docs (if available)

## Configuration

### Set Environment Variables

Before deployment, you may want to configure:

1. Press `Ctrl+Shift+P` > **Azure Developer: Environment Variables**
2. Or edit `.azure/<env-name>/.env` directly

Key variables:
```env
AZURE_LOCATION=eastus
EMAIL_SENDER_ADDRESS=noreply@yourdomain.com
EMAIL_DOMAIN=yourdomain.com
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
```

## Debugging

### Debug Function App

1. Set breakpoints in Python code
2. Press `F5` or click **Run and Debug**
3. Select "Attach to Python Functions"
4. The debugger will attach and hit your breakpoints

### View Logs

- **Function App Logs:** Check the Terminal panel when running locally
- **Web App Logs:** Check browser console (F12)
- **Azure Logs:** Use Azure Portal > Function App > Log Stream

## Monitoring Deployed Application

### View in Azure Portal

1. Press `Ctrl+Shift+P` > **Azure: Open in Portal**
2. Select your resource group

### View Application Insights

1. Navigate to Application Insights in Portal
2. View Live Metrics, Failures, Performance

### Stream Logs from Azure

```bash
# Function App logs
func azure functionapp logstream <function-app-name>

# Or use Azure CLI
az webapp log tail --name <function-app-name> --resource-group <resource-group-name>
```

## Troubleshooting

### "azd: command not found"

Install Azure Developer CLI:
- **Windows:** `winget install microsoft.azd`
- **macOS:** `brew tap azure/azd && brew install azd`
- **Linux:** `curl -fsSL https://aka.ms/install-azd.sh | bash`

### Function App won't start locally

1. Check that Azurite is running
2. Verify `local.settings.json` exists in the `api` folder
3. Ensure Python virtual environment is activated
4. Install dependencies: Run task "api: install dependencies"

### Web app build fails

1. Navigate to `web` folder
2. Run `npm install`
3. Check for TypeScript errors
4. Run task "web: build" to see detailed errors

### Deployment fails

1. Check Azure CLI login: `az account show`
2. Verify subscription is correct: `az account set --subscription <id>`
3. Check Bicep templates: Run task "bicep: validate infrastructure"
4. Review error messages in Terminal panel

## Tips

- Use **Workspace Trust** to enable all features
- Pin frequently used tasks to quick access
- Use **Split Terminal** to run multiple services simultaneously
- Enable **Auto Save** to avoid losing changes
- Use **Source Control** panel (Ctrl+Shift+G) to commit changes

## Next Steps

After deployment:

1. **Configure Authentication:**
   - Azure Portal > Static Web App > Authentication
   - Add Microsoft and Google providers

2. **Set Up Email Domain:**
   - Azure Portal > Communication Services
   - Configure email domain and sender address

3. **Monitor Application:**
   - Check Application Insights dashboard
   - Set up alerts for errors

4. **Set Up CI/CD:**
   - GitHub Actions workflows are generated by `azd`
   - Configure secrets in GitHub repository settings

## Keyboard Shortcuts

- `Ctrl+Shift+P` - Command Palette
- `F5` - Start Debugging
- `Ctrl+C` - Stop running task
- `Ctrl+Shift+B` - Run Build Task
- `Ctrl+Shift+T` - Reopen closed terminal
- `Ctrl+`` - Toggle Terminal

## Additional Resources

- [Azure Developer CLI Documentation](https://learn.microsoft.com/azure/developer/azure-developer-cli/)
- [VS Code Azure Extensions](https://code.visualstudio.com/docs/azure/extensions)
- [Azure Functions in VS Code](https://learn.microsoft.com/azure/azure-functions/functions-develop-vs-code)
- [Bicep Documentation](https://learn.microsoft.com/azure/azure-resource-manager/bicep/)

## Getting Help

- Check output in **Terminal** panel
- Review **Problems** panel for errors
- Check **Output** panel for extension logs
- Open an issue in the GitHub repository

## Clean Up

To delete all Azure resources:

1. Press `Ctrl+Shift+P`
2. Select **Tasks: Run Task**
3. Choose **azd: down (delete resources)**

Or use command:
```bash
azd down
```

This will delete all resources and free up Azure costs.
