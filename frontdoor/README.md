# Azure Front Door - Multi-App Router

This folder contains the infrastructure to deploy Azure Front Door for routing multiple applications under a single domain.

## Architecture

```
                    ┌─────────────────────────────────────┐
                    │       Azure Front Door              │
                    │  https://xxx.azurefd.net            │
                    │  (or custom domain)                 │
                    └─────────────────────────────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            │                       │                       │
     /research/*             /research/api/*           /ailab/*
            │                       │                       │
            ▼                       ▼                       ▼
   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
   │ Stock Research  │    │ Stock Research  │    │   AI Lab App    │
   │ Static Web App  │    │  Function App   │    │   (Future)      │
   └─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Features

- **Path-based routing**: Route different paths to different backend apps
- **HTTPS by default**: Automatic HTTP to HTTPS redirect
- **Caching**: Built-in CDN caching for static content
- **Compression**: Automatic gzip/brotli compression
- **Health probes**: Automatic backend health monitoring
- **Free SSL**: Managed SSL certificates for the default domain

## Routes

| Path | Backend | Description |
|------|---------|-------------|
| `/` | Stock Research SWA | Default landing page |
| `/research/*` | Stock Research SWA | Stock research frontend |
| `/research/api/*` | Stock Research Function App | Stock research API |
| `/ailab/*` | AI Lab App | AI Lab application (when configured) |

## Deployment

### Prerequisites

1. Azure CLI installed and logged in (`az login`)
2. Existing apps deployed (Static Web App, Function App, etc.)

### Quick Deploy

```powershell
# From the frontdoor folder
.\deploy.ps1
```

The script will automatically discover your deployed apps and configure the routes.

### Manual Deploy with Parameters

```powershell
.\deploy.ps1 `
    -StockResearchFrontend "xxx.azurestaticapps.net" `
    -StockResearchApi "xxx.azurewebsites.net" `
    -AiLabHost "xxx.azurewebsites.net"
```

### Deploy using Azure CLI directly

```powershell
az deployment sub create `
    --location eastus `
    --template-file infra/main.bicep `
    --parameters @infra/main.parameters.json `
    --parameters stockResearchFrontendHost="xxx.azurestaticapps.net" `
    --parameters stockResearchApiHost="xxx.azurewebsites.net"
```

## Adding a New App

1. Add new parameters to `main.bicep` and `main.parameters.json`:
   ```bicep
   @description('New App hostname')
   param newAppHost string = ''
   ```

2. Add origin group, origin, and route in `frontdoor.bicep` (follow the pattern for AI Lab)

3. Redeploy:
   ```powershell
   .\deploy.ps1 -NewAppHost "xxx.azurewebsites.net"
   ```

## Custom Domain

To add a custom domain (e.g., `app.sandeeprawat.com`):

1. In Azure Portal, go to the Front Door profile
2. Click "Domains" → "Add"
3. Enter your custom domain
4. Follow DNS validation steps
5. Associate the domain with your routes

Or add it via Bicep by adding a custom domain resource.

## Cost Estimation

Azure Front Door Standard tier:
- Base cost: ~$35/month
- Data transfer: $0.08/GB (first 10TB)
- Requests: $0.01 per 10,000 requests

For low-traffic personal apps, expect ~$35-50/month.

## Troubleshooting

### Routes not working
- Wait 10-15 minutes for Front Door to propagate
- Check the "Frontend domains" and "Backend pools" in Azure Portal
- Verify the backend health in "Health probes"

### CORS issues
- Add the Front Door domain to your backend's CORS settings
- The Function App needs to allow `https://xxx.azurefd.net`

### 404 errors on SPA routes
- Ensure your Static Web App has proper fallback routing configured
- Check `staticwebapp.config.json` for navigation fallback
