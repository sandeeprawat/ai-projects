#!/bin/bash

# Setup script for Stock Research Application
# This script helps you set up the development environment and deploy to Azure

set -e

echo "======================================"
echo "Stock Research App - Setup Script"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo "ℹ $1"
}

# Check prerequisites
echo "Checking prerequisites..."
echo ""

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python ${PYTHON_VERSION} installed"
else
    print_error "Python 3.10+ is required but not found"
    exit 1
fi

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    print_success "Node.js ${NODE_VERSION} installed"
else
    print_error "Node.js 18+ is required but not found"
    exit 1
fi

# Check Azure CLI
if command -v az &> /dev/null; then
    AZ_VERSION=$(az version --query '"azure-cli"' -o tsv)
    print_success "Azure CLI ${AZ_VERSION} installed"
else
    print_warning "Azure CLI not found - required for deployment"
fi

# Check Azure Developer CLI
if command -v azd &> /dev/null; then
    AZD_VERSION=$(azd version)
    print_success "Azure Developer CLI installed"
else
    print_warning "Azure Developer CLI not found - required for deployment"
    print_info "Install from: https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd"
fi

# Check Azure Functions Core Tools
if command -v func &> /dev/null; then
    FUNC_VERSION=$(func --version)
    print_success "Azure Functions Core Tools ${FUNC_VERSION} installed"
else
    print_warning "Azure Functions Core Tools not found - required for local development"
    print_info "Install from: https://learn.microsoft.com/azure/azure-functions/functions-run-local"
fi

echo ""
echo "======================================"
echo "What would you like to do?"
echo "======================================"
echo "1. Set up local development environment"
echo "2. Deploy to Azure (provision + deploy)"
echo "3. Provision Azure resources only"
echo "4. Deploy code only (resources must exist)"
echo "5. Validate infrastructure templates"
echo "6. Exit"
echo ""

read -p "Enter your choice (1-6): " choice

case $choice in
    1)
        echo ""
        echo "Setting up local development environment..."
        echo ""
        
        # Set up Python virtual environment
        cd api
        print_info "Creating Python virtual environment..."
        python3 -m venv ../.venv
        
        print_info "Activating virtual environment..."
        source ../.venv/bin/activate
        
        print_info "Installing Python dependencies..."
        pip install -r requirements.txt
        
        # Create local settings if not exists
        if [ ! -f "local.settings.json" ]; then
            print_info "Creating local.settings.json from example..."
            cp local.settings.json.example local.settings.json
            print_warning "Please edit api/local.settings.json with your Azure resource values"
        else
            print_info "local.settings.json already exists"
        fi
        
        cd ..
        
        # Set up Node.js
        cd web
        print_info "Installing Node.js dependencies..."
        npm install
        
        cd ..
        
        print_success "Local development environment set up successfully!"
        echo ""
        print_info "Next steps:"
        echo "  1. Edit api/local.settings.json with your Azure resource values"
        echo "  2. Start Azurite: azurite --silent --location .data/azurite"
        echo "  3. Start Functions: cd api && func start"
        echo "  4. Start Web: cd web && npm run dev"
        echo ""
        ;;
        
    2)
        echo ""
        echo "Deploying to Azure..."
        echo ""
        
        if ! command -v azd &> /dev/null; then
            print_error "Azure Developer CLI (azd) is required for deployment"
            exit 1
        fi
        
        # Check if logged in
        print_info "Checking Azure authentication..."
        if ! azd auth login --check-status &> /dev/null; then
            print_info "Logging in to Azure..."
            azd auth login
        else
            print_success "Already logged in to Azure"
        fi
        
        # Run azd up
        print_info "Running azd up (provision + deploy)..."
        azd up
        
        print_success "Deployment complete!"
        echo ""
        print_info "Next steps:"
        echo "  1. Configure authentication in Azure Static Web App"
        echo "  2. Set up email domain in Azure Communication Services"
        echo "  3. Test your application"
        echo ""
        ;;
        
    3)
        echo ""
        echo "Provisioning Azure resources..."
        echo ""
        
        if ! command -v azd &> /dev/null; then
            print_error "Azure Developer CLI (azd) is required"
            exit 1
        fi
        
        azd provision
        
        print_success "Provisioning complete!"
        ;;
        
    4)
        echo ""
        echo "Deploying code to Azure..."
        echo ""
        
        if ! command -v azd &> /dev/null; then
            print_error "Azure Developer CLI (azd) is required"
            exit 1
        fi
        
        azd deploy
        
        print_success "Deployment complete!"
        ;;
        
    5)
        echo ""
        echo "Validating infrastructure templates..."
        echo ""
        
        if ! command -v az &> /dev/null; then
            print_error "Azure CLI is required for validation"
            exit 1
        fi
        
        cd infra
        
        print_info "Building Bicep templates..."
        az bicep build --file main.bicep
        
        print_success "Validation complete!"
        echo ""
        print_info "Generated ARM template: infra/main.json"
        ;;
        
    6)
        echo "Exiting..."
        exit 0
        ;;
        
    *)
        print_error "Invalid choice"
        exit 1
        ;;
esac

echo ""
print_success "Done!"
