// Cognitive Services module (for Azure OpenAI and Bing Search)
param name string
param location string = resourceGroup().location
param tags object = {}
param kind string
param sku object

@description('Model deployments for OpenAI')
param deployments array = []

resource cognitiveService 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: name
  location: location
  tags: tags
  kind: kind
  sku: sku
  properties: {
    customSubDomainName: kind == 'OpenAI' ? name : null
    publicNetworkAccess: 'Enabled'
  }
}

resource deployment 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = [for deployment in deployments: {
  parent: cognitiveService
  name: deployment.name
  sku: deployment.sku
  properties: {
    model: deployment.model
  }
}]

output endpoint string = cognitiveService.properties.endpoint
output name string = cognitiveService.name
output key string = cognitiveService.listKeys().key1
