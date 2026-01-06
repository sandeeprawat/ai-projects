# Deep Research Application (Azure Durable Functions + Azure OpenAI)

Production-ready scaffold for deep research on a schedule using Azure Durable Functions and an Azure OpenAI-powered agent with Bing Web Search. Generates detailed reports (Markdown/HTML/PDF), stores history, and can email results. UI supports login with Microsoft/Google and scheduling recurrences.

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

- Provision + deploy with Azure Developer CLI:
  - `azd up` (from repo root) to provision resources and deploy /api and /web.
  - GitHub Actions will be generated for CI/CD.

## Next Steps (automation I will implement)

1) Create /api scaffold:
   - host.json, requirements.txt
   - Durable orchestrator and activity stubs
   - HTTP endpoints for schedules (create) and run_now
2) Add common utilities (config, models, openai_agent, bing, blob, cosmos, pdf, auth).
3) Add timer trigger for due schedules.
4) Generate minimal /web (React + Vite) with auth placeholder and simple forms.
5) Add /infra with azd + Bicep for one-command provisioning.

Once these are committed, iterate to full features (report viewer, downloads, email, history, SWA auth providers).
