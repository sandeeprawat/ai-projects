# AI Projects

A collection of AI-powered applications and tools showcasing modern cloud-native architectures and Azure AI services.

## 📋 Overview

This repository contains production-ready AI applications built with Azure services, demonstrating best practices for developing, deploying, and scaling intelligent systems.

## 🚀 Projects

### Deep Research Application

A production-ready application for deep research on a schedule using Azure Durable Functions and Azure OpenAI-powered agents with Bing Web Search integration.

**Key Features:**
- Automated deep research with scheduled recurrences
- AI-powered report generation (Markdown/HTML/PDF)
- User authentication (Microsoft/Google)
- Email delivery of research reports
- Historical report storage and management

**Tech Stack:**
- **Frontend:** React (Vite) on Azure Static Web Apps
- **Backend:** Python Azure Functions with Durable Functions
- **AI:** Azure OpenAI (GPT-4o) + Bing Search v7
- **Data:** Cosmos DB + Azure Blob Storage
- **Infrastructure:** Azure Developer CLI (azd) + Bicep

[📖 View Deep Research App Documentation](./stock-research-app/README.md)

## 🛠️ Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- Azure Functions Core Tools v4
- Azure CLI
- Azure Developer CLI (azd)
- An Azure subscription

### Repository Structure

```
.
├── stock-research-app/       # Deep research application
│   ├── api/                  # Azure Functions (Python)
│   ├── web/                  # React frontend
│   ├── scripts/              # Utility scripts
│   └── README.md             # Detailed project documentation
├── .vscode/                  # VS Code configuration
└── .gitignore                # Git ignore rules
```

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/sandeeprawat/ai-projects.git
   cd ai-projects
   ```

2. **Navigate to a project**
   ```bash
   cd stock-research-app
   ```

3. **Follow project-specific setup**
   
   See individual project READMEs for detailed setup and deployment instructions.

## 📚 Documentation

Each project contains its own comprehensive documentation:

- **Deep Research App:** [stock-research-app/README.md](./stock-research-app/README.md)

## 🔒 Security

- All secrets are managed via Azure Key Vault with Managed Identity
- Authentication is handled by Azure Static Web Apps (Microsoft/Google)
- No hardcoded credentials in the codebase

## 📊 Observability

All applications include:
- Azure Application Insights integration
- Durable Functions telemetry
- Structured logging and monitoring

## 🤝 Contributing

This is a personal project repository. If you find issues or have suggestions, feel free to open an issue.

## 📄 License

This project is available for educational and reference purposes.

## 🔗 Links

- [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/)
- [Azure Functions](https://learn.microsoft.com/azure/azure-functions/)
- [Azure OpenAI Service](https://learn.microsoft.com/azure/ai-services/openai/)
- [Azure Durable Functions](https://learn.microsoft.com/azure/azure-functions/durable/)

---

**Author:** Sandeep Rawat  
**Repository:** [github.com/sandeeprawat/ai-projects](https://github.com/sandeeprawat/ai-projects)
