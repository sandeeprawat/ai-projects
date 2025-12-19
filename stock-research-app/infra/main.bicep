// Main Bicep template for Stock Research Application
targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the environment which is used to generate a short unique hash used in all resources.')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

@description('Id of the user or app to assign application roles')
param principalId string = ''

// Optional parameters with defaults
@description('Azure OpenAI Deployment Name')
param openAiDeploymentName string = 'gpt-4o-mini'

@description('Azure OpenAI Model Name')
param openAiModelName string = 'gpt-4o-mini'

@description('Azure OpenAI Model Version')
param openAiModelVersion string = '2024-07-18'

@description('Azure OpenAI SKU')
param openAiSkuName string = 'S0'

@description('Email sender address for Azure Communication Services')
param emailSenderAddress string = ''

@description('Email domain for Azure Communication Services')
param emailDomain string = ''

// Generate a unique suffix for resources
var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var tags = { 'azd-env-name': environmentName }

// Resource group
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: '${abbrs.resourcesResourceGroups}${environmentName}'
  location: location
  tags: tags
}

// Cosmos DB Account
module cosmos './core/database/cosmos-account.bicep' = {
  name: 'cosmos'
  scope: rg
  params: {
    name: '${abbrs.documentDBDatabaseAccounts}${resourceToken}'
    location: location
    tags: tags
    databases: [
      {
        name: 'stockresearch'
        containers: [
          {
            name: 'schedules'
            partitionKey: '/userId'
          }
          {
            name: 'runs'
            partitionKey: '/userId'
          }
          {
            name: 'reports'
            partitionKey: '/userId'
          }
        ]
      }
    ]
  }
}

// Storage Account
module storage './core/storage/storage-account.bicep' = {
  name: 'storage'
  scope: rg
  params: {
    name: '${abbrs.storageStorageAccounts}${resourceToken}'
    location: location
    tags: tags
    containers: [
      {
        name: 'reports'
      }
    ]
  }
}

// Application Insights
module monitoring './core/monitor/monitoring.bicep' = {
  name: 'monitoring'
  scope: rg
  params: {
    location: location
    tags: tags
    logAnalyticsName: '${abbrs.operationalInsightsWorkspaces}${resourceToken}'
    applicationInsightsName: '${abbrs.insightsComponents}${resourceToken}'
  }
}

// Key Vault
module keyVault './core/security/keyvault.bicep' = {
  name: 'keyvault'
  scope: rg
  params: {
    name: '${abbrs.keyVaultVaults}${resourceToken}'
    location: location
    tags: tags
    principalId: principalId
  }
}

// Azure OpenAI Service
module openAi './core/ai/cognitiveservices.bicep' = {
  name: 'openai'
  scope: rg
  params: {
    name: '${abbrs.cognitiveServicesAccounts}${resourceToken}'
    location: location
    tags: tags
    kind: 'OpenAI'
    sku: {
      name: openAiSkuName
    }
    deployments: [
      {
        name: openAiDeploymentName
        model: {
          format: 'OpenAI'
          name: openAiModelName
          version: openAiModelVersion
        }
        sku: {
          name: 'Standard'
          capacity: 30
        }
      }
    ]
  }
}

// Bing Search v7 (Azure AI Services)
module bingSearch './core/ai/cognitiveservices.bicep' = {
  name: 'bing-search'
  scope: rg
  params: {
    name: '${abbrs.cognitiveServicesAccounts}bing-${resourceToken}'
    location: 'global'
    tags: tags
    kind: 'Bing.Search.v7'
    sku: {
      name: 'S1'
    }
  }
}

// Azure Communication Services
module communicationServices './core/communication/communication-services.bicep' = {
  name: 'communication-services'
  scope: rg
  params: {
    name: '${abbrs.communicationServices}${resourceToken}'
    location: 'global'
    tags: tags
    emailServiceName: '${abbrs.communicationServicesEmailServices}${resourceToken}'
    emailDomain: emailDomain
  }
}

// Function App with Managed Identity
module functionApp './core/host/functions.bicep' = {
  name: 'functions'
  scope: rg
  params: {
    name: '${abbrs.webSitesFunctions}${resourceToken}'
    location: location
    tags: tags
    applicationInsightsName: monitoring.outputs.applicationInsightsName
    appServicePlanId: appServicePlan.outputs.id
    runtimeName: 'python'
    runtimeVersion: '3.10'
    storageAccountName: storage.outputs.name
    appSettings: {
      AZURE_OPENAI_ENDPOINT: openAi.outputs.endpoint
      AZURE_OPENAI_DEPLOYMENT: openAiDeploymentName
      AZURE_OPENAI_API_VERSION: '2024-06-01'
      BING_V7_ENDPOINT: 'https://api.bing.microsoft.com'
      COSMOS_DB_URL: cosmos.outputs.endpoint
      COSMOS_DB_NAME: 'stockresearch'
      REPORTS_CONTAINER: 'reports'
      ACS_CONNECTION_STRING: communicationServices.outputs.connectionString
      EMAIL_SENDER: emailSenderAddress
      APP_BASE_URL: 'https://${abbrs.webSitesFunctions}${resourceToken}.azurewebsites.net'
    }
  }
}

// App Service Plan for Functions
module appServicePlan './core/host/appserviceplan.bicep' = {
  name: 'appserviceplan'
  scope: rg
  params: {
    name: '${abbrs.webServerFarms}${resourceToken}'
    location: location
    tags: tags
    sku: {
      name: 'Y1'
      tier: 'Dynamic'
    }
  }
}

// Static Web App
module web './core/host/staticwebapp.bicep' = {
  name: 'web'
  scope: rg
  params: {
    name: '${abbrs.webStaticSites}${resourceToken}'
    location: location
    tags: tags
    sku: {
      name: 'Free'
      tier: 'Free'
    }
  }
}

// Role assignments for Function App Managed Identity
module cosmosRoleAssignment './core/security/role.bicep' = {
  name: 'cosmos-role-assignment'
  scope: rg
  params: {
    principalId: functionApp.outputs.identityPrincipalId
    roleDefinitionId: '00000000-0000-0000-0000-000000000002' // Cosmos DB Built-in Data Contributor
    principalType: 'ServicePrincipal'
  }
}

module storageRoleAssignment './core/security/role.bicep' = {
  name: 'storage-role-assignment'
  scope: rg
  params: {
    principalId: functionApp.outputs.identityPrincipalId
    roleDefinitionId: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe' // Storage Blob Data Contributor
    principalType: 'ServicePrincipal'
  }
}

module keyVaultRoleAssignment './core/security/role.bicep' = {
  name: 'keyvault-role-assignment'
  scope: rg
  params: {
    principalId: functionApp.outputs.identityPrincipalId
    roleDefinitionId: '4633458b-17de-408a-b874-0445c86b69e6' // Key Vault Secrets User
    principalType: 'ServicePrincipal'
  }
}

// Store secrets in Key Vault
module secrets './core/security/keyvault-secrets.bicep' = {
  name: 'secrets'
  scope: rg
  params: {
    keyVaultName: keyVault.outputs.name
    secrets: [
      {
        name: 'AZURE-OPENAI-API-KEY'
        value: openAi.outputs.key
      }
      {
        name: 'BING-V7-KEY'
        value: bingSearch.outputs.key
      }
      {
        name: 'COSMOS-DB-KEY'
        value: cosmos.outputs.key
      }
    ]
  }
}

// Outputs
output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_RESOURCE_GROUP string = rg.name

output AZURE_OPENAI_ENDPOINT string = openAi.outputs.endpoint
output AZURE_OPENAI_DEPLOYMENT string = openAiDeploymentName

output COSMOS_DB_URL string = cosmos.outputs.endpoint
output COSMOS_DB_NAME string = 'stockresearch'

output STORAGE_ACCOUNT_NAME string = storage.outputs.name
output REPORTS_CONTAINER string = 'reports'

output FUNCTION_APP_NAME string = functionApp.outputs.name
output FUNCTION_APP_URL string = functionApp.outputs.uri

output STATIC_WEB_APP_NAME string = web.outputs.name
output STATIC_WEB_APP_URL string = web.outputs.uri

output KEY_VAULT_NAME string = keyVault.outputs.name
output APPLICATION_INSIGHTS_NAME string = monitoring.outputs.applicationInsightsName
