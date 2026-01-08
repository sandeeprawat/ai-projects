targetScope = 'subscription'

@description('Name of the Front Door profile')
param frontDoorName string = 'sanrawat-frontdoor'

@description('Primary location for the resource group')
param location string = 'global'

@description('Resource group name')
param resourceGroupName string = 'sanrawat-app'

@description('Tags for all resources')
param tags object = {
  'purpose': 'multi-app-routing'
  'managed-by': 'bicep'
}

// App origins - add your apps here
@description('Stock Research App - Static Web App hostname (e.g., xxx.azurestaticapps.net)')
param stockResearchFrontendHost string = ''

@description('Stock Research App - Function App hostname (e.g., xxx.azurewebsites.net)')
param stockResearchApiHost string = ''

@description('AI Lab App - hostname (optional, for future use)')
param aiLabHost string = ''

// Use existing resource group
resource rg 'Microsoft.Resources/resourceGroups@2022-09-01' existing = {
  name: resourceGroupName
}

// Deploy Front Door resources
module frontDoor 'frontdoor.bicep' = {
  name: 'frontdoor-deployment'
  scope: rg
  params: {
    frontDoorName: frontDoorName
    tags: tags
    stockResearchFrontendHost: stockResearchFrontendHost
    stockResearchApiHost: stockResearchApiHost
    aiLabHost: aiLabHost
  }
}

output frontDoorEndpoint string = frontDoor.outputs.frontDoorEndpoint
output frontDoorId string = frontDoor.outputs.frontDoorId
