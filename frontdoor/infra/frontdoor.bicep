targetScope = 'resourceGroup'

@description('Name of the Front Door profile')
param frontDoorName string

@description('Tags for resources')
param tags object

// App origins
@description('Stock Research App - Static Web App hostname')
param stockResearchFrontendHost string

@description('Stock Research App - Function App hostname')
param stockResearchApiHost string

@description('AI Lab App - hostname (optional)')
param aiLabHost string = ''

// Front Door Profile (Standard tier for cost-effectiveness)
resource frontDoorProfile 'Microsoft.Cdn/profiles@2023-05-01' = {
  name: frontDoorName
  location: 'global'
  tags: tags
  sku: {
    name: 'Standard_AzureFrontDoor'
  }
}

// Default Endpoint (using Azure-provided domain)
resource frontDoorEndpoint 'Microsoft.Cdn/profiles/afdEndpoints@2023-05-01' = {
  parent: frontDoorProfile
  name: 'default-endpoint'
  location: 'global'
  properties: {
    enabledState: 'Enabled'
  }
}

// ============================================
// STOCK RESEARCH APP - Origin Group & Origins
// ============================================

// Origin Group for Stock Research Frontend (Static Web App)
resource stockResearchFrontendOriginGroup 'Microsoft.Cdn/profiles/originGroups@2023-05-01' = if (!empty(stockResearchFrontendHost)) {
  parent: frontDoorProfile
  name: 'stock-research-frontend'
  properties: {
    loadBalancingSettings: {
      sampleSize: 4
      successfulSamplesRequired: 3
      additionalLatencyInMilliseconds: 50
    }
    healthProbeSettings: {
      probePath: '/'
      probeRequestType: 'HEAD'
      probeProtocol: 'Https'
      probeIntervalInSeconds: 100
    }
    sessionAffinityState: 'Disabled'
  }
}

// Origin for Stock Research Frontend
resource stockResearchFrontendOrigin 'Microsoft.Cdn/profiles/originGroups/origins@2023-05-01' = if (!empty(stockResearchFrontendHost)) {
  parent: stockResearchFrontendOriginGroup
  name: 'swa-origin'
  properties: {
    hostName: stockResearchFrontendHost
    httpPort: 80
    httpsPort: 443
    originHostHeader: stockResearchFrontendHost
    priority: 1
    weight: 1000
    enabledState: 'Enabled'
  }
}

// Origin Group for Stock Research API (Function App)
resource stockResearchApiOriginGroup 'Microsoft.Cdn/profiles/originGroups@2023-05-01' = if (!empty(stockResearchApiHost)) {
  parent: frontDoorProfile
  name: 'stock-research-api'
  properties: {
    loadBalancingSettings: {
      sampleSize: 4
      successfulSamplesRequired: 3
      additionalLatencyInMilliseconds: 50
    }
    healthProbeSettings: {
      probePath: '/api/health'
      probeRequestType: 'GET'
      probeProtocol: 'Https'
      probeIntervalInSeconds: 100
    }
    sessionAffinityState: 'Disabled'
  }
}

// Origin for Stock Research API
resource stockResearchApiOrigin 'Microsoft.Cdn/profiles/originGroups/origins@2023-05-01' = if (!empty(stockResearchApiHost)) {
  parent: stockResearchApiOriginGroup
  name: 'func-origin'
  properties: {
    hostName: stockResearchApiHost
    httpPort: 80
    httpsPort: 443
    originHostHeader: stockResearchApiHost
    priority: 1
    weight: 1000
    enabledState: 'Enabled'
  }
}

// ============================================
// AI LAB APP - Origin Group & Origins (Future)
// ============================================

// Origin Group for AI Lab App
resource aiLabOriginGroup 'Microsoft.Cdn/profiles/originGroups@2023-05-01' = if (!empty(aiLabHost)) {
  parent: frontDoorProfile
  name: 'ailab-app'
  properties: {
    loadBalancingSettings: {
      sampleSize: 4
      successfulSamplesRequired: 3
      additionalLatencyInMilliseconds: 50
    }
    healthProbeSettings: {
      probePath: '/'
      probeRequestType: 'HEAD'
      probeProtocol: 'Https'
      probeIntervalInSeconds: 100
    }
    sessionAffinityState: 'Disabled'
  }
}

// Origin for AI Lab App
resource aiLabOrigin 'Microsoft.Cdn/profiles/originGroups/origins@2023-05-01' = if (!empty(aiLabHost)) {
  parent: aiLabOriginGroup
  name: 'ailab-origin'
  properties: {
    hostName: aiLabHost
    httpPort: 80
    httpsPort: 443
    originHostHeader: aiLabHost
    priority: 1
    weight: 1000
    enabledState: 'Enabled'
  }
}

// ============================================
// ROUTES - Path-based routing
// ============================================

// Route for /research/* -> Stock Research Frontend
resource stockResearchRoute 'Microsoft.Cdn/profiles/afdEndpoints/routes@2023-05-01' = if (!empty(stockResearchFrontendHost)) {
  parent: frontDoorEndpoint
  name: 'research-route'
  properties: {
    originGroup: {
      id: stockResearchFrontendOriginGroup.id
    }
    originPath: '/'
    patternsToMatch: [
      '/research'
      '/research/*'
    ]
    supportedProtocols: [
      'Http'
      'Https'
    ]
    httpsRedirect: 'Enabled'
    forwardingProtocol: 'HttpsOnly'
    linkToDefaultDomain: 'Enabled'
    cacheConfiguration: {
      queryStringCachingBehavior: 'IgnoreQueryString'
      compressionSettings: {
        isCompressionEnabled: true
        contentTypesToCompress: [
          'text/html'
          'text/css'
          'application/javascript'
          'application/json'
          'image/svg+xml'
        ]
      }
    }
  }
  dependsOn: [
    stockResearchFrontendOrigin
  ]
}

// Route for /research/api/* -> Stock Research API
resource stockResearchApiRoute 'Microsoft.Cdn/profiles/afdEndpoints/routes@2023-05-01' = if (!empty(stockResearchApiHost)) {
  parent: frontDoorEndpoint
  name: 'research-api-route'
  properties: {
    originGroup: {
      id: stockResearchApiOriginGroup.id
    }
    originPath: '/api'
    patternsToMatch: [
      '/research/api/*'
    ]
    supportedProtocols: [
      'Http'
      'Https'
    ]
    httpsRedirect: 'Enabled'
    forwardingProtocol: 'HttpsOnly'
    linkToDefaultDomain: 'Enabled'
  }
  dependsOn: [
    stockResearchApiOrigin
    stockResearchRoute // Ensure order for route priority
  ]
}

// Route for /ailab/* -> AI Lab App (when configured)
resource aiLabRoute 'Microsoft.Cdn/profiles/afdEndpoints/routes@2023-05-01' = if (!empty(aiLabHost)) {
  parent: frontDoorEndpoint
  name: 'ailab-route'
  properties: {
    originGroup: {
      id: aiLabOriginGroup.id
    }
    originPath: '/'
    patternsToMatch: [
      '/ailab'
      '/ailab/*'
    ]
    supportedProtocols: [
      'Http'
      'Https'
    ]
    httpsRedirect: 'Enabled'
    forwardingProtocol: 'HttpsOnly'
    linkToDefaultDomain: 'Enabled'
    cacheConfiguration: {
      queryStringCachingBehavior: 'IgnoreQueryString'
      compressionSettings: {
        isCompressionEnabled: true
        contentTypesToCompress: [
          'text/html'
          'text/css'
          'application/javascript'
          'application/json'
          'image/svg+xml'
        ]
      }
    }
  }
  dependsOn: [
    aiLabOrigin
  ]
}

// Default route (root path) -> Stock Research Frontend (or customize as needed)
resource defaultRoute 'Microsoft.Cdn/profiles/afdEndpoints/routes@2023-05-01' = if (!empty(stockResearchFrontendHost)) {
  parent: frontDoorEndpoint
  name: 'default-route'
  properties: {
    originGroup: {
      id: stockResearchFrontendOriginGroup.id
    }
    patternsToMatch: [
      '/'
      '/*'
    ]
    supportedProtocols: [
      'Http'
      'Https'
    ]
    httpsRedirect: 'Enabled'
    forwardingProtocol: 'HttpsOnly'
    linkToDefaultDomain: 'Enabled'
    cacheConfiguration: {
      queryStringCachingBehavior: 'IgnoreQueryString'
      compressionSettings: {
        isCompressionEnabled: true
        contentTypesToCompress: [
          'text/html'
          'text/css'
          'application/javascript'
          'application/json'
          'image/svg+xml'
        ]
      }
    }
  }
  dependsOn: [
    stockResearchFrontendOrigin
    stockResearchRoute
    stockResearchApiRoute
  ]
}

output frontDoorEndpoint string = 'https://${frontDoorEndpoint.properties.hostName}'
output frontDoorId string = frontDoorProfile.id
output frontDoorHostName string = frontDoorEndpoint.properties.hostName
