#!/usr/bin/env pwsh
# Deployment script for Deep Research App to Azure

param(
    [string]$ResourceGroup = "sanrawat-app",
    [string]$Location = "centralindia"
)

$ErrorActionPreference = "Stop"

Write-Host "================================" -ForegroundColor Cyan
Write-Host "Deep Research App - Azure Deployment" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Load environment variables from .env file
$envFile = ".azure/stock-research/.env"
if (Test-Path $envFile) {
    Write-Host "Loading environment variables from $envFile..." -ForegroundColor Yellow
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]*)\s*=\s*"?([^"]*)"?\s*$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

# Step 1: Deploy Infrastructure
Write-Host "Step 1: Deploying infrastructure..." -ForegroundColor Green
$deploymentName = "stock-research-$(Get-Date -Format 'yyyyMMdd-HHmmss')"

az deployment group create `
    --resource-group $ResourceGroup `
    --template-file infra/main.bicep `
    --parameters infra/main.bicepparam `
    --name $deploymentName `
    --query "properties.outputs" -o json | ConvertFrom-Json | Tee-Object -Variable outputs

if ($LASTEXITCODE -ne 0) {
    Write-Error "Infrastructure deployment failed"
    exit 1
}

$functionAppName = $outputs.AZURE_FUNCTION_APP_NAME.value
$staticWebAppName = $outputs.AZURE_STATIC_WEB_APP_NAME.value

Write-Host ""
Write-Host "Infrastructure deployed successfully!" -ForegroundColor Green
Write-Host "  Function App: $functionAppName" -ForegroundColor Cyan
Write-Host "  Static Web App: $staticWebAppName" -ForegroundColor Cyan
Write-Host ""

# Step 2: Deploy Function App
Write-Host "Step 2: Deploying Azure Functions..." -ForegroundColor Green
Push-Location api

# Create deployment package
Write-Host "  Creating deployment package..." -ForegroundColor Yellow
$tempZip = "$env:TEMP\functionapp.zip"
if (Test-Path $tempZip) { Remove-Item $tempZip -Force }

# Compress Python function app
Compress-Archive -Path * -DestinationPath $tempZip -Force

# Deploy to Azure
Write-Host "  Deploying to Azure..." -ForegroundColor Yellow
az functionapp deployment source config-zip `
    --resource-group $ResourceGroup `
    --name $functionAppName `
    --src $tempZip

Pop-Location

if ($LASTEXITCODE -ne 0) {
    Write-Error "Function App deployment failed"
    exit 1
}

Write-Host "Function App deployed successfully!" -ForegroundColor Green
Write-Host ""

# Step 3: Deploy Static Web App
Write-Host "Step 3: Deploying Static Web App..." -ForegroundColor Green
Write-Host "  Note: Static Web Apps are typically deployed via GitHub Actions" -ForegroundColor Yellow
Write-Host "  You can deploy manually using 'swa deploy' command" -ForegroundColor Yellow
Write-Host ""

# Step 4: Display URLs
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Function App URL: $($outputs.AZURE_FUNCTION_APP_URL.value)" -ForegroundColor Cyan
Write-Host "Static Web App URL: $($outputs.AZURE_STATIC_WEB_APP_URL.value)" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Test the Function App: $($outputs.AZURE_FUNCTION_APP_URL.value)/api/schedules" -ForegroundColor White
Write-Host "  2. Deploy Static Web App: cd web && swa deploy" -ForegroundColor White
Write-Host "  3. Update CORS settings if needed" -ForegroundColor White
Write-Host ""
