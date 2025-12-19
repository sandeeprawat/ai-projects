# Quick Reference - Stock Research Application

## 🚀 Deployment Commands

| Command | Description |
|---------|-------------|
| `azd up` | Provision + Deploy everything |
| `azd provision` | Create Azure resources only |
| `azd deploy` | Deploy code only |
| `azd down` | Delete all Azure resources |
| `azd env new <name>` | Create new environment |
| `azd env list` | List environments |

## 🛠️ Local Development

### Start All Services

```bash
# Terminal 1: Storage emulator
azurite --silent --location .data/azurite

# Terminal 2: Functions API
cd api
func start

# Terminal 3: Web frontend
cd web
npm run dev
```

### Endpoints

- **Frontend:** http://localhost:5174
- **API:** http://localhost:7071
- **Azurite:** 
  - Blob: http://localhost:10000
  - Queue: http://localhost:10001
  - Table: http://localhost:10002

## 📋 VS Code Tasks

Access via `Ctrl+Shift+P` → **Tasks: Run Task**

**Deployment:**
- azd: up (provision + deploy)
- azd: provision
- azd: deploy
- azd: down

**Development:**
- func: host start
- web: start (vite dev)
- Start Azurite

**Build:**
- web: build
- api: install dependencies
- bicep: validate infrastructure

## 🔧 Prerequisites

| Tool | Version | Install Link |
|------|---------|--------------|
| Python | 3.10+ | https://www.python.org/downloads/ |
| Node.js | 18+ | https://nodejs.org/ |
| Azure CLI | Latest | https://aka.ms/azure-cli |
| Azure Developer CLI | Latest | https://aka.ms/install-azd |
| Azure Functions Core Tools | v4 | https://aka.ms/func-tools |

## 📁 Project Structure

```
stock-research-app/
├── api/                    # Azure Functions (Python)
│   ├── common/            # Shared utilities
│   ├── orchestrators/     # Durable orchestrators
│   ├── activities/        # Durable activities
│   ├── http/              # HTTP triggers
│   └── requirements.txt   # Python dependencies
├── web/                    # React frontend (Vite)
│   ├── src/               # Source code
│   └── package.json       # Node.js dependencies
├── infra/                  # Infrastructure as Code
│   ├── main.bicep         # Main template
│   └── core/              # Reusable modules
├── .azure/                 # azd environment config
├── setup.sh               # Setup script (Linux/Mac)
├── setup.ps1              # Setup script (Windows)
├── azure.yaml             # azd configuration
└── DEPLOYMENT.md          # Full deployment guide
```

## 🔑 Environment Variables

### Required for Deployment

```bash
export AZURE_ENV_NAME="stock-research-dev"
export AZURE_LOCATION="eastus"
export AZURE_SUBSCRIPTION_ID="your-subscription-id"
```

### Optional Configuration

```bash
export AZURE_OPENAI_DEPLOYMENT="gpt-4o-mini"
export EMAIL_SENDER_ADDRESS="noreply@yourdomain.com"
export EMAIL_DOMAIN="yourdomain.com"
```

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| `azd: command not found` | Install Azure Developer CLI |
| Function app won't start | 1. Check Azurite is running<br>2. Verify local.settings.json exists |
| Web build fails | Run `npm install` in web directory |
| Deployment fails | 1. Check `az account show`<br>2. Run `azd auth login` |
| Bicep validation fails | Run `az bicep build --file infra/main.bicep` |

## 📊 Azure Resources Created

| Resource | Purpose | SKU |
|----------|---------|-----|
| Static Web App | Frontend hosting | Free |
| Functions App | Backend API | Consumption (Y1) |
| Cosmos DB | Database | Serverless |
| Storage Account | Blob storage | Standard LRS |
| Azure OpenAI | AI model | S0 |
| Bing Search v7 | Web search | S1 |
| Communication Services | Email | Pay-as-you-go |
| Key Vault | Secrets | Standard |
| App Insights | Monitoring | Pay-as-you-go |

## 🔒 Security Best Practices

- ✅ Managed Identity for service-to-service auth
- ✅ Secrets stored in Key Vault
- ✅ HTTPS enforced on all endpoints
- ✅ RBAC instead of access keys
- ✅ Public blob access disabled
- ✅ TLS 1.2 minimum

## 📈 Monitoring

### View Logs

```bash
# Function App logs
func azure functionapp logstream <function-app-name>

# Azure CLI
az webapp log tail --name <function-app-name> --resource-group <rg-name>
```

### Application Insights

1. Azure Portal → Application Insights
2. View: Live Metrics, Failures, Performance

## 💰 Cost Estimates (Monthly)

| Scenario | Estimated Cost* |
|----------|----------------|
| Development (light usage) | ~$10-30 |
| Production (moderate) | ~$50-200 |
| Production (heavy) | $200+ |

*Estimates vary based on usage. Monitor actual costs in Azure Portal.

## 📚 Documentation

- [DEPLOYMENT.md](./DEPLOYMENT.md) - Complete deployment guide
- [VSCODE_QUICKSTART.md](./VSCODE_QUICKSTART.md) - VS Code quick start
- [infra/README.md](./infra/README.md) - Infrastructure documentation
- [Main README](./README.md) - Project overview

## 🆘 Getting Help

1. Check troubleshooting section above
2. Review [Azure Functions docs](https://learn.microsoft.com/azure/azure-functions/)
3. Check [azd documentation](https://learn.microsoft.com/azure/developer/azure-developer-cli/)
4. Open an issue on GitHub

## 🧹 Clean Up

### Delete All Resources

```bash
azd down
```

Or manually:
```bash
az group delete --name rg-<env-name> --yes
```

---

**Need more details?** See [DEPLOYMENT.md](./DEPLOYMENT.md) for comprehensive instructions.
