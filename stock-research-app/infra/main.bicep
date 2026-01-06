targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the environment (e.g., dev, prod)')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

@description('Name of the resource group')
param resourceGroupName string = 'rg-${environmentName}'

// Existing resources (already provisioned)
@description('Existing Storage Account name')
param existingStorageAccountName string

@description('Existing Cosmos DB account name')
param existingCosmosDbAccountName string

@description('Existing resource group for existing resources')
param existingResourceGroup string

// Secrets
@secure()
@description('Azure OpenAI API key')
param azureOpenAiApiKey string

@description('Azure OpenAI endpoint')
param azureOpenAiEndpoint string

@description('Azure OpenAI deployment name')
param azureOpenAiDeployment string = 'gpt-4o'

@secure()
@description('Azure Communication Services connection string')
param acsConnectionString string

@description('Email sender address')
param emailSender string

@secure()
@description('Bing Search API key (optional)')
param bingV7Key string = ''

var resourceToken = uniqueString(subscription().id, location, environmentName)
var tags = { 'azd-env-name': environmentName }

// Resource Group
resource rg 'Microsoft.Resources/resourceGroups@2022-09-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

// Deploy all resources
module resources 'resources.bicep' = {
  name: 'resources-${resourceToken}'
  scope: rg
  params: {
    location: location
    environmentName: environmentName
    resourceToken: resourceToken
    tags: tags
    existingStorageAccountName: existingStorageAccountName
    existingCosmosDbAccountName: existingCosmosDbAccountName
    existingResourceGroup: existingResourceGroup
    azureOpenAiApiKey: azureOpenAiApiKey
    azureOpenAiEndpoint: azureOpenAiEndpoint
    azureOpenAiDeployment: azureOpenAiDeployment
    acsConnectionString: acsConnectionString
    emailSender: emailSender
    bingV7Key: bingV7Key
  }
}

output RESOURCE_GROUP_ID string = rg.id
output AZURE_FUNCTION_APP_NAME string = resources.outputs.functionAppName
output AZURE_FUNCTION_APP_URL string = resources.outputs.functionAppUrl
output AZURE_STATIC_WEB_APP_NAME string = resources.outputs.staticWebAppName
output AZURE_STATIC_WEB_APP_URL string = resources.outputs.staticWebAppUrl
