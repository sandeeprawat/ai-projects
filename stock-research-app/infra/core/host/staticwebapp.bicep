// Static Web App module
param name string
param location string
param tags object = {}
param sku object = {
  name: 'Free'
  tier: 'Free'
}

resource staticWebApp 'Microsoft.Web/staticSites@2022-09-01' = {
  name: name
  location: location
  tags: tags
  sku: sku
  properties: {
    buildProperties: {
      skipGithubActionWorkflowGeneration: true
    }
  }
}

output name string = staticWebApp.name
output uri string = 'https://${staticWebApp.properties.defaultHostname}'
output id string = staticWebApp.id
