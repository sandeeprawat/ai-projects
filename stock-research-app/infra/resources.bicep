targetScope = 'resourceGroup'

@description('Location for resources')
param location string

@description('Environment name')
param environmentName string

@description('Resource token for unique naming')
param resourceToken string

@description('Tags for resources')
param tags object

// Existing resources
param existingStorageAccountName string
param existingCosmosDbAccountName string
param existingResourceGroup string

// Secrets
@secure()
param azureOpenAiApiKey string
param azureOpenAiEndpoint string
param azureOpenAiDeployment string
@secure()
param acsConnectionString string
param emailSender string
@secure()
param bingV7Key string

// Azure AI Projects settings for Deep Research
param azureAiProjectsDeepResearchEndpoint string = ''
param azureAiProjectsDeepResearchProject string = ''
param deepResearchModelDeploymentName string = 'o3-deep-research'

// Azure AI Projects settings for Agent Mode
param azureAiProjectsAgentModeEndpoint string = ''
param azureAiProjectsAgentModeProject string = ''
param azureAiProjectsAgentModeAgentId string = ''

// Model deployment name
param modelDeploymentName string = 'gpt-4o'

// Bing resource name for Azure AI connection
param bingResourceName string = ''

// User-Assigned Managed Identity (required by AZD)
resource userIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'azid${resourceToken}'
  location: location
  tags: tags
}

// Storage Account for Function App
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'azst${resourceToken}'
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true // Required for Function App
    supportsHttpsTrafficOnly: true
  }
}

// Reports blob container
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

resource reportsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'reports'
  properties: {
    publicAccess: 'None'
  }
}

// Role assignments for managed identity on storage
resource storageBlobDataOwnerRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, userIdentity.id, 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b')
    principalId: userIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource storageBlobDataContributorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, userIdentity.id, 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
    principalId: userIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource storageQueueDataContributorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, userIdentity.id, '974c5e8b-45b9-4653-ba55-5f855dd0fb88')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '974c5e8b-45b9-4653-ba55-5f855dd0fb88')
    principalId: userIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource storageTableDataContributorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, userIdentity.id, '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3')
    principalId: userIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Cosmos DB role assignment deployed to the existing resource group
module cosmosRoleAssignment 'cosmos-role.bicep' = {
  name: 'cosmos-role-${resourceToken}'
  scope: resourceGroup(existingResourceGroup)
  params: {
    cosmosDbAccountName: existingCosmosDbAccountName
    principalId: userIdentity.properties.principalId
  }
}

// Log Analytics Workspace
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: 'azlog${resourceToken}'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// Application Insights
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'azai${resourceToken}'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

// Monitoring Metrics Publisher role for managed identity
resource monitoringMetricsPublisherRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(appInsights.id, userIdentity.id, '3913510d-42f4-4e42-8a64-420c390055eb')
  scope: appInsights
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '3913510d-42f4-4e42-8a64-420c390055eb')
    principalId: userIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// App Service Plan (Consumption)
resource appServicePlan 'Microsoft.Web/serverfarms@2022-09-01' = {
  name: 'azplan${resourceToken}'
  location: location
  tags: tags
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  kind: 'functionapp'
  properties: {
    reserved: true
  }
}

// Function App
resource functionApp 'Microsoft.Web/sites@2022-09-01' = {
  name: 'azfunc${resourceToken}'
  location: location
  tags: union(tags, { 'azd-service-name': 'api' })
  kind: 'functionapp,linux'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${userIdentity.id}': {}
    }
  }
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      appSettings: [
        {
          // Runtime storage must use connection string on Linux Consumption (Azure Files doesn't support MI)
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=${environment().suffixes.storage}'
        }
        {
          name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=${environment().suffixes.storage}'
        }
        {
          name: 'WEBSITE_CONTENTSHARE'
          value: toLower('azfunc${resourceToken}')
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: appInsights.properties.InstrumentationKey
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsights.properties.ConnectionString
        }
        {
          name: 'AZURE_OPENAI_ENDPOINT'
          value: azureOpenAiEndpoint
        }
        {
          name: 'AZURE_OPENAI_API_KEY'
          value: azureOpenAiApiKey
        }
        {
          name: 'AZURE_OPENAI_API_VERSION'
          value: '2024-10-21'
        }
        {
          name: 'AZURE_OPENAI_DEPLOYMENT'
          value: azureOpenAiDeployment
        }
        {
          name: 'COSMOS_DB_URL'
          value: 'https://${existingCosmosDbAccountName}.documents.azure.com:443/'
        }
        {
          name: 'COSMOS_DB_NAME'
          value: 'stockresearch'
        }
        {
          name: 'AZURE_STORAGE_ACCOUNT_NAME'
          value: storageAccount.name
        }
        {
          name: 'AZURE_CLIENT_ID'
          value: userIdentity.properties.clientId
        }
        {
          name: 'REPORTS_CONTAINER'
          value: 'reports'
        }
        {
          name: 'ACS_CONNECTION_STRING'
          value: acsConnectionString
        }
        {
          name: 'EMAIL_SENDER'
          value: emailSender
        }
        {
          name: 'BING_V7_ENDPOINT'
          value: 'https://api.bing.microsoft.com'
        }
        {
          name: 'BING_V7_KEY'
          value: bingV7Key
        }
        {
          name: 'APP_BASE_URL'
          value: 'https://azfunc${resourceToken}.azurewebsites.net'
        }
        {
          name: 'AZURE_AI_PROJECTS_DEEPRESEARCH_ENDPOINT'
          value: azureAiProjectsDeepResearchEndpoint
        }
        {
          name: 'AZURE_AI_PROJECTS_DEEPRESEARCH_PROJECT'
          value: azureAiProjectsDeepResearchProject
        }
        {
          name: 'DEEP_RESEARCH_MODEL_DEPLOYMENT_NAME'
          value: deepResearchModelDeploymentName
        }
        {
          name: 'AZURE_AI_PROJECTS_AGENTMODE_ENDPOINT'
          value: azureAiProjectsAgentModeEndpoint
        }
        {
          name: 'AZURE_AI_PROJECTS_AGENTMODE_PROJECT'
          value: azureAiProjectsAgentModeProject
        }
        {
          name: 'AZURE_AI_PROJECTS_AGENTMODE_AGENT_ID'
          value: azureAiProjectsAgentModeAgentId
        }
        {
          name: 'MODEL_DEPLOYMENT_NAME'
          value: modelDeploymentName
        }
        {
          name: 'BING_RESOURCE_NAME'
          value: bingResourceName
        }
      ]
      cors: {
        allowedOrigins: [
          'https://portal.azure.com'
          'https://black-rock-0a7d0690f.1.azurestaticapps.net'
        ]
        supportCredentials: false
      }
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
    }
    httpsOnly: true
  }
}

// Diagnostic settings for Function App
resource functionAppDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'functionapp-diagnostics'
  scope: functionApp
  properties: {
    workspaceId: logAnalytics.id
    logs: [
      {
        category: 'FunctionAppLogs'
        enabled: true
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
      }
    ]
  }
}

// Static Web App for frontend
resource staticWebApp 'Microsoft.Web/staticSites@2022-09-01' = {
  name: 'azswa${resourceToken}'
  location: 'eastus2' // Static Web Apps have limited region availability
  tags: union(tags, { 'azd-service-name': 'web' })
  sku: {
    name: 'Free'
    tier: 'Free'
  }
  properties: {
    buildProperties: {
      appLocation: 'web'
      outputLocation: 'dist'
    }
  }
}

// Static Web App configuration
resource staticWebAppConfig 'Microsoft.Web/staticSites/config@2022-09-01' = {
  parent: staticWebApp
  name: 'appsettings'
  properties: {
    API_BASE_URL: 'https://${functionApp.properties.defaultHostName}/api'
  }
}

output functionAppName string = functionApp.name
output functionAppUrl string = 'https://${functionApp.properties.defaultHostName}'
output staticWebAppName string = staticWebApp.name
output staticWebAppUrl string = 'https://${staticWebApp.properties.defaultHostname}'
