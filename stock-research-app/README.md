# Stock Research Application (Azure Durable Functions + Azure OpenAI)

Production-ready scaffold to research stocks on a schedule using Azure Durable Functions and an Azure OpenAI-powered agent with Bing Web Search. Generates detailed reports (Markdown/HTML/PDF), stores history, and can email results. UI supports login with Microsoft/Google and scheduling recurrences.

## Architecture

- Frontend: React (Vite) hosted on Azure Static Web Apps (SWA) with built-in auth (Microsoft + Google).
- Backend: Python Azure Functions with Durable Functions (orchestrator + activities).
- Data: Cosmos DB (schedules, runs, reports metadata).
- Files: Azure Blob Storage (report files md/html/pdf).
- Email: Azure Communication Services (Email).
- AI: Azure OpenAI (GPT-4o or o4-mini) + Bing Search v7 (Azure AI Services).
- Secrets: Azure Key Vault with Managed Identity.
- Observability: App Insights + Durable telemetry.

## Repository Layout

- /infra
  - Azure Developer CLI (azd) + Bicep templates (provision SWA, Function App, Cosmos, Storage, Key Vault, OpenAI, Bing Search, ACS Email, App Insights)
- /api (Azure Functions Python)
  - host.json, requirements.txt
  - orchestrators/research_orchestrator (Durable orchestrator)
  - activities/ (fetch_context, synthesize_report, save_report, send_email)
  - http/ (schedules CRUD, run_now, reports)
  - timers/due_scheduler (checks due schedules and starts orchestrations)
  - common/ (auth, cosmos, blob, openai_agent, bing, pdf, config, models)
- /web (React + Vite)
  - Pages: Dashboard, Schedules, Runs, Reports, Report Viewer
  - Components: ScheduleForm, RecurrencePicker, ReportCard, Viewer
  - Auth via SWA; API client

## Data Model (Cosmos DB)

- schedules: id, userId, symbols[], recurrence {type: daily|weekly|hours, hour|dow|interval}, nextRunAt, email {to[], attachPdf}, createdAt, active
- runs: id, scheduleId, userId, startedAt, status, durationMs, error
- reports: id, runId, scheduleId, userId, title, symbols[], period, summary, blobPaths {md, html, pdf?}, createdAt, citations[]

## Minimal Vertical Slice (to be implemented first)

- API: POST /api/schedules (create), POST /api/schedules/{id}/run (run now)
- Durable Orchestrator:
  1) fetch_context (Bing search + fetch pages + extract)
  2) synthesize_report (Azure OpenAI with citations)
  3) save_report (Blob + Cosmos)
  4) send_email (optional)
- Web: Simple form to create schedule and button to run now; report viewer with download links.

## Prerequisites

- Python 3.10+
- Node 18+ (for web)
- Azure Functions Core Tools v4
- Azure CLI + Azure Developer CLI (azd)
- An Azure subscription with:
  - Azure OpenAI resource and model deployment (e.g., gpt-4o or o4-mini)
  - Azure AI Services (Bing Search v7)
  - Azure Communication Services (Email)
  - Permissions to create SWA, Function App, Cosmos, Storage, Key Vault, App Insights

## Local Development (after scaffold completes)

- API
  1) Create `stock-research-app/api/local.settings.json` from the template and fill env vars.
  2) Install deps: `pip install -r requirements.txt`
  3) Start functions: `func start`
- Web
  1) `cd stock-research-app/web`
  2) `npm install`
  3) `npm run dev`

## Deployment

### Quick Start Options

Choose the method that works best for you:

#### Option 1: Automated Setup Script (Recommended for first-time setup)

**Linux/macOS:**
```bash
cd stock-research-app
chmod +x setup.sh
./setup.sh
```

**Windows (PowerShell):**
```powershell
cd stock-research-app
.\setup.ps1
```

The setup script will:
- Check prerequisites
- Guide you through local development setup or Azure deployment
- Validate infrastructure templates

#### Option 2: Azure Developer CLI (azd)

```bash
cd stock-research-app

# First-time: Initialize and deploy
azd up

# Subsequent deployments
azd deploy
```

#### Option 3: VS Code Quick Deploy

See [VSCODE_QUICKSTART.md](./VSCODE_QUICKSTART.md) for step-by-step VS Code deployment instructions.

### Comprehensive Documentation

- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Complete deployment guide with all options
- **[VSCODE_QUICKSTART.md](./VSCODE_QUICKSTART.md)** - VS Code-specific quick start
- **[infra/README.md](./infra/README.md)** - Infrastructure as Code documentation

### What Gets Provisioned

The deployment creates these Azure resources:
- Azure Static Web App (frontend)
- Azure Functions App (backend)
- Cosmos DB (database)
- Azure Storage (blob storage)
- Azure OpenAI (AI model)
- Bing Search v7 (web search)
- Azure Communication Services (email)
- Key Vault (secrets)
- Application Insights (monitoring)

### CI/CD with GitHub Actions

A GitHub Actions workflow is included at `.github/workflows/azure-deploy.yml` for automated deployments on push to main branch.

Required secrets:
- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `AZURE_LOCATION`

Or use `AZURE_CREDENTIALS` for service principal authentication.
