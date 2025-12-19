// Cosmos DB Account module
param name string
param location string = resourceGroup().location
param tags object = {}

@description('Database configurations')
param databases array = []

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2023-04-15' = {
  name: name
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    databaseAccountOfferType: 'Standard'
    enableAutomaticFailover: false
    enableMultipleWriteLocations: false
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
  }
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-04-15' = [for db in databases: {
  parent: cosmosAccount
  name: db.name
  properties: {
    resource: {
      id: db.name
    }
  }
}]

// Create all containers across all databases
// Using index-based approach to handle up to 10 containers per database
resource container0 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = [for (db, i) in databases: if (length(db.containers) > 0) {
  parent: database[i]
  name: db.containers[0].name
  properties: {
    resource: {
      id: db.containers[0].name
      partitionKey: {
        paths: [db.containers[0].partitionKey]
        kind: 'Hash'
      }
    }
  }
}]

resource container1 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = [for (db, i) in databases: if (length(db.containers) > 1) {
  parent: database[i]
  name: db.containers[1].name
  properties: {
    resource: {
      id: db.containers[1].name
      partitionKey: {
        paths: [db.containers[1].partitionKey]
        kind: 'Hash'
      }
    }
  }
}]

resource container2 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = [for (db, i) in databases: if (length(db.containers) > 2) {
  parent: database[i]
  name: db.containers[2].name
  properties: {
    resource: {
      id: db.containers[2].name
      partitionKey: {
        paths: [db.containers[2].partitionKey]
        kind: 'Hash'
      }
    }
  }
}]

output endpoint string = cosmosAccount.properties.documentEndpoint
output name string = cosmosAccount.name
output key string = cosmosAccount.listKeys().primaryMasterKey
