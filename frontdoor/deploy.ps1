# Deploy Azure Front Door for multi-app routing
# Usage: .\deploy.ps1 -StockResearchFrontend "xxx.azurestaticapps.net" -StockResearchApi "xxx.azurewebsites.net"

param(
    [Parameter(Mandatory=$false)]
    [string]$FrontDoorName = "sanrawat-frontdoor",
    
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroupName = "sanrawat-app",
    
    [Parameter(Mandatory=$false)]
    [string]$StockResearchFrontend = "",
    
    [Parameter(Mandatory=$false)]
    [string]$StockResearchApi = "",
    
    [Parameter(Mandatory=$false)]
    [string]$AiLabHost = "",
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "global"
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Deploying Azure Front Door..." -ForegroundColor Cyan
Write-Host ""

# Check if logged into Azure
$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Host "❌ Not logged into Azure. Please run 'az login' first." -ForegroundColor Red
    exit 1
}

Write-Host "📍 Using subscription: $($account.name)" -ForegroundColor Yellow
Write-Host "📍 Resource Group: $ResourceGroupName" -ForegroundColor Yellow
Write-Host ""

# If hostnames not provided, try to discover them
if (-not $StockResearchFrontend -or -not $StockResearchApi) {
    Write-Host "🔍 Discovering existing app hostnames..." -ForegroundColor Yellow
    
    # Find Static Web Apps
    $swaList = az staticwebapp list --resource-group $ResourceGroupName 2>$null | ConvertFrom-Json
    if ($swaList -and $swaList.Count -gt 0) {
        $StockResearchFrontend = $swaList[0].defaultHostname
        Write-Host "   Found Static Web App: $StockResearchFrontend" -ForegroundColor Green
    }
    
    # Find Function Apps
    $funcList = az functionapp list --resource-group $ResourceGroupName 2>$null | ConvertFrom-Json
    if ($funcList -and $funcList.Count -gt 0) {
        $StockResearchApi = $funcList[0].defaultHostName
        Write-Host "   Found Function App: $StockResearchApi" -ForegroundColor Green
    }
    
    # Also check stock-research resource group
    $stockRg = "rg-stockresearch-prod"
    $swaListStock = az staticwebapp list --resource-group $stockRg 2>$null | ConvertFrom-Json
    if ($swaListStock -and $swaListStock.Count -gt 0 -and -not $StockResearchFrontend) {
        $StockResearchFrontend = $swaListStock[0].defaultHostname
        Write-Host "   Found Static Web App in $stockRg : $StockResearchFrontend" -ForegroundColor Green
    }
    
    $funcListStock = az functionapp list --resource-group $stockRg 2>$null | ConvertFrom-Json
    if ($funcListStock -and $funcListStock.Count -gt 0 -and -not $StockResearchApi) {
        $StockResearchApi = $funcListStock[0].defaultHostName
        Write-Host "   Found Function App in $stockRg : $StockResearchApi" -ForegroundColor Green
    }
    
    Write-Host ""
}

# Validate we have at least one origin
if (-not $StockResearchFrontend -and -not $StockResearchApi -and -not $AiLabHost) {
    Write-Host "⚠️  No app hostnames found or provided. Front Door will be created without routes." -ForegroundColor Yellow
    Write-Host "   You can add routes later by updating the parameters and redeploying." -ForegroundColor Yellow
    Write-Host ""
}

# Display configuration
Write-Host "📋 Configuration:" -ForegroundColor Cyan
Write-Host "   Front Door Name: $FrontDoorName"
Write-Host "   Stock Research Frontend: $(if ($StockResearchFrontend) { $StockResearchFrontend } else { '(not configured)' })"
Write-Host "   Stock Research API: $(if ($StockResearchApi) { $StockResearchApi } else { '(not configured)' })"
Write-Host "   AI Lab Host: $(if ($AiLabHost) { $AiLabHost } else { '(not configured)' })"
Write-Host ""

# Confirm deployment
$confirm = Read-Host "Proceed with deployment? (y/N)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "Deployment cancelled." -ForegroundColor Yellow
    exit 0
}

# Deploy using Bicep
Write-Host ""
Write-Host "🔨 Deploying Bicep template..." -ForegroundColor Cyan

$deploymentName = "frontdoor-$(Get-Date -Format 'yyyyMMddHHmmss')"

az deployment sub create `
    --name $deploymentName `
    --location "eastus" `
    --template-file "$PSScriptRoot\infra\main.bicep" `
    --parameters frontDoorName=$FrontDoorName `
    --parameters resourceGroupName=$ResourceGroupName `
    --parameters stockResearchFrontendHost=$StockResearchFrontend `
    --parameters stockResearchApiHost=$StockResearchApi `
    --parameters aiLabHost=$AiLabHost

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Deployment successful!" -ForegroundColor Green
    Write-Host ""
    
    # Get the Front Door endpoint
    $fd = az afd endpoint list --profile-name $FrontDoorName --resource-group $ResourceGroupName 2>$null | ConvertFrom-Json
    if ($fd -and $fd.Count -gt 0) {
        $endpoint = $fd[0].hostName
        Write-Host "🌐 Front Door Endpoint: https://$endpoint" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "📍 Available Routes:" -ForegroundColor Yellow
        if ($StockResearchFrontend) {
            Write-Host "   https://$endpoint/research -> Stock Research App"
        }
        if ($StockResearchApi) {
            Write-Host "   https://$endpoint/research/api/* -> Stock Research API"
        }
        if ($AiLabHost) {
            Write-Host "   https://$endpoint/ailab -> AI Lab App"
        }
        Write-Host "   https://$endpoint/ -> Default (Stock Research)"
    }
} else {
    Write-Host ""
    Write-Host "❌ Deployment failed!" -ForegroundColor Red
    exit 1
}
