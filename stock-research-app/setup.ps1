# Setup script for Stock Research Application (PowerShell)
# This script helps you set up the development environment and deploy to Azure

$ErrorActionPreference = "Stop"

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Stock Research App - Setup Script" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Function to print colored output
function Print-Success {
    param($Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Print-Error {
    param($Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Print-Warning {
    param($Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

function Print-Info {
    param($Message)
    Write-Host "ℹ $Message" -ForegroundColor White
}

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Cyan
Write-Host ""

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Print-Success "Python $pythonVersion installed"
} catch {
    Print-Error "Python 3.10+ is required but not found"
    exit 1
}

# Check Node.js
try {
    $nodeVersion = node --version
    Print-Success "Node.js $nodeVersion installed"
} catch {
    Print-Error "Node.js 18+ is required but not found"
    exit 1
}

# Check Azure CLI
try {
    $azVersion = az version --query '\"azure-cli\"' -o tsv
    Print-Success "Azure CLI $azVersion installed"
} catch {
    Print-Warning "Azure CLI not found - required for deployment"
}

# Check Azure Developer CLI
try {
    $azdVersion = azd version
    Print-Success "Azure Developer CLI installed"
} catch {
    Print-Warning "Azure Developer CLI not found - required for deployment"
    Print-Info "Install from: https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd"
}

# Check Azure Functions Core Tools
try {
    $funcVersion = func --version
    Print-Success "Azure Functions Core Tools $funcVersion installed"
} catch {
    Print-Warning "Azure Functions Core Tools not found - required for local development"
    Print-Info "Install from: https://learn.microsoft.com/azure/azure-functions/functions-run-local"
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "What would you like to do?" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "1. Set up local development environment"
Write-Host "2. Deploy to Azure (provision + deploy)"
Write-Host "3. Provision Azure resources only"
Write-Host "4. Deploy code only (resources must exist)"
Write-Host "5. Validate infrastructure templates"
Write-Host "6. Exit"
Write-Host ""

$choice = Read-Host "Enter your choice (1-6)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "Setting up local development environment..." -ForegroundColor Cyan
        Write-Host ""
        
        # Set up Python virtual environment
        Set-Location api
        Print-Info "Creating Python virtual environment..."
        python -m venv ..\.venv
        
        Print-Info "Activating virtual environment..."
        & ..\.venv\Scripts\Activate.ps1
        
        Print-Info "Installing Python dependencies..."
        pip install -r requirements.txt
        
        # Create local settings if not exists
        if (-not (Test-Path "local.settings.json")) {
            Print-Info "Creating local.settings.json from example..."
            Copy-Item local.settings.json.example local.settings.json
            Print-Warning "Please edit api\local.settings.json with your Azure resource values"
        } else {
            Print-Info "local.settings.json already exists"
        }
        
        Set-Location ..
        
        # Set up Node.js
        Set-Location web
        Print-Info "Installing Node.js dependencies..."
        npm install
        
        Set-Location ..
        
        Print-Success "Local development environment set up successfully!"
        Write-Host ""
        Print-Info "Next steps:"
        Write-Host "  1. Edit api\local.settings.json with your Azure resource values"
        Write-Host "  2. Start Azurite: azurite --silent --location .data\azurite"
        Write-Host "  3. Start Functions: cd api; func start"
        Write-Host "  4. Start Web: cd web; npm run dev"
        Write-Host ""
    }
    
    "2" {
        Write-Host ""
        Write-Host "Deploying to Azure..." -ForegroundColor Cyan
        Write-Host ""
        
        if (-not (Get-Command azd -ErrorAction SilentlyContinue)) {
            Print-Error "Azure Developer CLI (azd) is required for deployment"
            exit 1
        }
        
        # Check if logged in
        Print-Info "Checking Azure authentication..."
        try {
            azd auth login --check-status | Out-Null
            Print-Success "Already logged in to Azure"
        } catch {
            Print-Info "Logging in to Azure..."
            azd auth login
        }
        
        # Run azd up
        Print-Info "Running azd up (provision + deploy)..."
        azd up
        
        Print-Success "Deployment complete!"
        Write-Host ""
        Print-Info "Next steps:"
        Write-Host "  1. Configure authentication in Azure Static Web App"
        Write-Host "  2. Set up email domain in Azure Communication Services"
        Write-Host "  3. Test your application"
        Write-Host ""
    }
    
    "3" {
        Write-Host ""
        Write-Host "Provisioning Azure resources..." -ForegroundColor Cyan
        Write-Host ""
        
        if (-not (Get-Command azd -ErrorAction SilentlyContinue)) {
            Print-Error "Azure Developer CLI (azd) is required"
            exit 1
        }
        
        azd provision
        
        Print-Success "Provisioning complete!"
    }
    
    "4" {
        Write-Host ""
        Write-Host "Deploying code to Azure..." -ForegroundColor Cyan
        Write-Host ""
        
        if (-not (Get-Command azd -ErrorAction SilentlyContinue)) {
            Print-Error "Azure Developer CLI (azd) is required"
            exit 1
        }
        
        azd deploy
        
        Print-Success "Deployment complete!"
    }
    
    "5" {
        Write-Host ""
        Write-Host "Validating infrastructure templates..." -ForegroundColor Cyan
        Write-Host ""
        
        if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
            Print-Error "Azure CLI is required for validation"
            exit 1
        }
        
        Set-Location infra
        
        Print-Info "Building Bicep templates..."
        az bicep build --file main.bicep
        
        Print-Success "Validation complete!"
        Write-Host ""
        Print-Info "Generated ARM template: infra\main.json"
    }
    
    "6" {
        Write-Host "Exiting..."
        exit 0
    }
    
    default {
        Print-Error "Invalid choice"
        exit 1
    }
}

Write-Host ""
Print-Success "Done!"
